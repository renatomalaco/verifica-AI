from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from contracts import (
    AcceptInviteRequest,
    CreateInviteRequest,
    DisableAccountRequest,
    LoginRequest,
    ResearchAccountStatus,
    ResearchPermission,
    ResearchRole,
    ResearchRoleInfo,
    ResearchUser,
    SaveRoleRequest,
)


def test_research_role_values_match_frontend_contract():
    # Consumed by web/src/domain/research.ts; changing them breaks the side navigation.
    assert [r.value for r in ResearchRole] == ["admin", "researcher"]


def test_login_request_trims_and_lowercases_the_email():
    assert LoginRequest(email="  Banca@Exemplo.com ", password="x").email == "banca@exemplo.com"


@pytest.mark.parametrize(
    "payload", [{"email": "", "password": "x"}, {"email": "a@b.c", "password": ""}]
)
def test_login_request_rejects_empty_fields(payload):
    with pytest.raises(ValidationError):
        LoginRequest.model_validate(payload)


def test_accept_invite_request_requires_a_token():
    with pytest.raises(ValidationError):
        AcceptInviteRequest(token="", password="uma-senha-bem-longa")


def test_research_user_serializes_its_role_with_permissions_and_optional_expiry():
    expires = datetime(2026, 12, 20, tzinfo=timezone.utc)
    role = ResearchRoleInfo(
        id="orientador", name="Orientador", permissions=[ResearchPermission.RUN_STUDY]
    )
    user = ResearchUser(email="banca@exemplo.com", role=role, expires_at=expires)

    assert user.model_dump(mode="json") == {
        "email": "banca@exemplo.com",
        "role": {"id": "orientador", "name": "Orientador", "permissions": ["run_study"]},
        "expires_at": "2026-12-20T00:00:00Z",
    }


def test_permission_values_match_frontend_contract():
    # Consumed by web/src/types; the admin screen words each one.
    assert [p.value for p in ResearchPermission] == ["run_study", "manage_access"]


def test_save_role_request_trims_the_name_and_drops_repeated_permissions():
    request = SaveRoleRequest(name="  Orientador ", permissions=["run_study", "run_study"])

    assert request.name == "Orientador"
    assert request.permissions == [ResearchPermission.RUN_STUDY]


@pytest.mark.parametrize("name", ["", "   ", "x" * 61])
def test_save_role_request_needs_a_short_name(name):
    with pytest.raises(ValidationError):
        SaveRoleRequest(name=name)


def test_account_status_values_match_frontend_contract():
    # Consumed by web/src/types; the admin screen words each one.
    assert [s.value for s in ResearchAccountStatus] == ["active", "invited", "expired", "disabled"]


def test_create_invite_request_normalizes_the_email_and_defaults_to_researcher():
    request = CreateInviteRequest(email=" Banca@Exemplo.com ")

    assert request.email == "banca@exemplo.com"
    assert request.role == ResearchRole.RESEARCHER
    assert request.expires_on is None


def test_create_invite_request_reads_the_last_day_as_a_date():
    request = CreateInviteRequest.model_validate(
        {"email": "a@b.c", "role": "admin", "expires_on": "2026-12-20"}
    )

    assert request.expires_on == date(2026, 12, 20)


def test_disable_account_request_normalizes_the_email():
    assert DisableAccountRequest(email=" Banca@Exemplo.com").email == "banca@exemplo.com"
