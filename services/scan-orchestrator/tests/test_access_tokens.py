from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from contracts import ResearchRole
from scan_orchestrator.domain.research_access import Principal
from scan_orchestrator.infrastructure.access_tokens import (
    AccessTokenIssuer,
    AccessTokenVerifier,
    generate_key_pair,
)
from scan_orchestrator.infrastructure.passwords import PasswordHasher

PRIVATE_KEY, PUBLIC_KEY = generate_key_pair()


def test_a_signed_access_token_carries_the_account_and_role():
    account_id = uuid4()
    token = AccessTokenIssuer(PRIVATE_KEY).issue(account_id, ResearchRole.ADMIN)

    assert AccessTokenVerifier(PUBLIC_KEY).verify(token) == Principal(account_id, ResearchRole.ADMIN)


def test_the_access_token_lasts_fifteen_minutes():
    issued = datetime.now(timezone.utc) - timedelta(minutes=16)
    token = AccessTokenIssuer(PRIVATE_KEY, clock=lambda: issued).issue(uuid4(), ResearchRole.ADMIN)

    assert AccessTokenVerifier(PUBLIC_KEY).verify(token) is None


def test_a_token_signed_by_another_key_is_rejected():
    other_private, _ = generate_key_pair()
    token = AccessTokenIssuer(other_private).issue(uuid4(), ResearchRole.ADMIN)

    assert AccessTokenVerifier(PUBLIC_KEY).verify(token) is None


def test_an_unsigned_token_is_rejected():
    forged = jwt.encode({"sub": str(uuid4()), "role": "admin"}, key=None, algorithm="none")

    assert AccessTokenVerifier(PUBLIC_KEY).verify(forged) is None


@pytest.mark.parametrize("token", [None, "", "not-a-jwt"])
def test_missing_or_garbage_tokens_are_rejected(token):
    assert AccessTokenVerifier(PUBLIC_KEY).verify(token) is None


def test_a_verifier_without_a_key_rejects_everything():
    # Fail closed: a service deployed without the public key must not let anyone in.
    token = AccessTokenIssuer(PRIVATE_KEY).issue(uuid4(), ResearchRole.ADMIN)

    assert AccessTokenVerifier("").verify(token) is None


def test_an_issuer_needs_the_private_key():
    with pytest.raises(ValueError):
        AccessTokenIssuer("")


def test_passwords_are_hashed_with_argon2_and_verified():
    hasher = PasswordHasher()
    hashed = hasher.hash("uma-senha-bem-longa")

    assert hashed.startswith("$argon2id$")
    assert hasher.verify("uma-senha-bem-longa", hashed)
    assert not hasher.verify("outra-senha-qualquer", hashed)


def test_verifying_against_no_hash_is_false():
    # Unknown e-mails still run a hash, so timing does not reveal which accounts exist.
    assert not PasswordHasher().verify("uma-senha-bem-longa", None)
