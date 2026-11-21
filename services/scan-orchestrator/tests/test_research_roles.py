import pytest

from contracts import ResearchPermission, ResearchRole
from scan_orchestrator.application.research_roles import (
    ResearchRoles,
    RoleNameTakenError,
    UnknownRoleError,
)
from scan_orchestrator.domain.research_access import ProtectedRoleError
from scan_orchestrator.infrastructure.research_account_repository import (
    InMemoryResearchAccountRepository,
)

RUN = frozenset({ResearchPermission.RUN_STUDY})


@pytest.fixture
def roles() -> ResearchRoles:
    return ResearchRoles(InMemoryResearchAccountRepository())


async def test_a_new_role_gets_its_own_id_name_and_permissions(roles):
    role = await roles.create("Orientador", RUN)

    assert role.id.startswith("cargo-")
    assert (role.name, role.permissions) == ("Orientador", RUN)
    assert role in await roles.list()


async def test_roles_are_listed_by_name(roles):
    await roles.create("Banca", frozenset())

    assert [r.name for r in await roles.list()] == ["Administrador", "Banca", "Pesquisador"]


async def test_two_roles_cannot_share_a_name_whatever_the_case(roles):
    await roles.create("Orientador", RUN)

    with pytest.raises(RoleNameTakenError):
        await roles.create("orientador", frozenset())


async def test_editing_a_role_keeps_its_id_and_may_keep_its_own_name(roles):
    role = await roles.create("Orientador", frozenset())

    same_name = await roles.update(role.id, "Orientador", RUN)
    renamed = await roles.update(role.id, "Coorientador", RUN)

    assert same_name.permissions == RUN
    assert (renamed.id, renamed.name) == (role.id, "Coorientador")


async def test_editing_cannot_take_the_name_of_another_role(roles):
    role = await roles.create("Orientador", frozenset())

    with pytest.raises(RoleNameTakenError):
        await roles.update(role.id, "Pesquisador", frozenset())


async def test_editing_an_unknown_role_is_refused(roles):
    with pytest.raises(UnknownRoleError):
        await roles.update("cargo-nao-existe", "Fantasma", frozenset())


async def test_the_admin_role_cannot_lose_access_management(roles):
    with pytest.raises(ProtectedRoleError):
        await roles.update(ResearchRole.ADMIN, "Administrador", RUN)

    renamed = await roles.update(
        ResearchRole.ADMIN, "Autor", frozenset({ResearchPermission.MANAGE_ACCESS})
    )
    assert renamed.name == "Autor"
