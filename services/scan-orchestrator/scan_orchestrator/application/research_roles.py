"""Roles of the research area: admins name them and choose what each one may do."""

from contracts import ResearchPermission
from scan_orchestrator.domain.research_access import Role, check_role_change, new_role_id
from scan_orchestrator.infrastructure.research_account_repository import ResearchAccountRepository


class RoleNameTakenError(Exception):
    pass


class UnknownRoleError(Exception):
    pass


class ResearchRoles:
    def __init__(self, repository: ResearchAccountRepository) -> None:
        self._repo = repository

    async def list(self) -> list[Role]:
        return sorted(await self._repo.list_roles(), key=lambda role: role.name.casefold())

    async def create(self, name: str, permissions: frozenset[ResearchPermission]) -> Role:
        await self._ensure_name_is_free(name, role_id=None)
        role = Role(new_role_id(), name, permissions)
        await self._repo.save_role(role)
        return role

    async def update(
        self, role_id: str, name: str, permissions: frozenset[ResearchPermission]
    ) -> Role:
        if await self._repo.get_role(role_id) is None:
            raise UnknownRoleError(role_id)
        check_role_change(role_id, permissions)
        await self._ensure_name_is_free(name, role_id=role_id)
        role = Role(role_id, name, permissions)
        await self._repo.save_role(role)
        return role

    async def _ensure_name_is_free(self, name: str, role_id: str | None) -> None:
        for role in await self._repo.list_roles():
            if role.id != role_id and role.name.casefold() == name.casefold():
                raise RoleNameTakenError(name)
