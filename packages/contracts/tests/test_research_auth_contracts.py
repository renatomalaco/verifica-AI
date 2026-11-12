from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from contracts import AcceptInviteRequest, LoginRequest, ResearchRole, ResearchUser


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


def test_research_user_serializes_role_and_optional_expiry():
    expires = datetime(2026, 12, 20, tzinfo=timezone.utc)
    user = ResearchUser(email="banca@exemplo.com", role=ResearchRole.RESEARCHER, expires_at=expires)

    assert user.model_dump(mode="json") == {
        "email": "banca@exemplo.com",
        "role": "researcher",
        "expires_at": "2026-12-20T00:00:00Z",
    }
