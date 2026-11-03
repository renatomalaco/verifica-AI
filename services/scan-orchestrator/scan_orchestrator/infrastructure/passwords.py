from pwdlib import PasswordHash


class PasswordHasher:
    """Argon2id via pwdlib; no hand-written cryptography."""

    def __init__(self) -> None:
        self._hash = PasswordHash.recommended()
        self._dummy_hash = self._hash.hash("timing-equalizer")

    def hash(self, password: str) -> str:
        return self._hash.hash(password)

    def verify(self, password: str, password_hash: str | None) -> bool:
        if password_hash is None:
            # Pay the same cost as a real check, so the response time does not reveal unknown accounts.
            self._hash.verify(password, self._dummy_hash)
            return False
        return self._hash.verify(password, password_hash)
