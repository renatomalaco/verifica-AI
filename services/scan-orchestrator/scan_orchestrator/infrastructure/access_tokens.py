"""Access tokens (R5a): 15-minute JWTs signed with Ed25519.

Only the orchestrator holds the private key and issues tokens; the research-runner gets
just the public key, so it can check a token but never mint one.
"""

import base64
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import UUID

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from contracts import ResearchPermission
from scan_orchestrator.domain.research_access import Principal, Role

ACCESS_TOKEN_TTL = timedelta(minutes=15)
ALGORITHM = "EdDSA"
ISSUER = "verifica-ai"


def generate_key_pair() -> tuple[str, str]:
    """Returns (private, public) as base64 of the raw 32-byte keys, one line each for the .env."""
    private = Ed25519PrivateKey.generate()
    public_raw = private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    private_raw = private.private_bytes_raw()
    return base64.b64encode(private_raw).decode("ascii"), base64.b64encode(public_raw).decode(
        "ascii"
    )


class AccessTokenIssuer:
    def __init__(
        self,
        private_key_b64: str,
        clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if not private_key_b64:
            raise ValueError("AUTH_JWT_PRIVATE_KEY is not set")
        self._key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
        self._clock = clock

    def issue(self, account_id: UUID, role: Role) -> str:
        """The permissions travel in the token, so the research-runner can check them alone.
        A role change reaches a signed-in account at its next renewal, within 15 minutes."""
        now = self._clock()
        claims = {
            "sub": str(account_id),
            "role": role.id,
            "perms": [p.value for p in role.sorted_permissions()],
            "iss": ISSUER,
            "iat": now,
            "exp": now + ACCESS_TOKEN_TTL,
        }
        return jwt.encode(claims, self._key, algorithm=ALGORITHM)


class AccessTokenVerifier:
    def __init__(self, public_key_b64: str) -> None:
        self._key = (
            Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
            if public_key_b64
            else None
        )

    def verify(self, token: str | None) -> Principal | None:
        """The caller behind a valid token, or None for anything missing, forged or expired."""
        if self._key is None or not token:
            return None
        try:
            claims = jwt.decode(
                token,
                self._key,
                algorithms=[ALGORITHM],
                issuer=ISSUER,
                options={"require": ["sub", "exp", "role", "perms"]},
            )
            return Principal(
                account_id=UUID(claims["sub"]),
                role=claims["role"],
                permissions=frozenset(ResearchPermission(p) for p in claims["perms"]),
            )
        except (jwt.InvalidTokenError, ValueError):
            return None
