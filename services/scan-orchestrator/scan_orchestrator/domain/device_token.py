import hashlib
import hmac
from uuid import UUID, uuid4

# Anonymous device token (R5b): "<uuid>.<hmac-sha256>". It does not identify the person;
# it only counts the "Me explica" quota without requiring an account.


def _signature(device_id: str, secret: bytes) -> str:
    return hmac.new(secret, device_id.encode("ascii"), hashlib.sha256).hexdigest()


def issue_device_token(secret: bytes) -> tuple[str, str]:
    device_id = str(uuid4())
    return device_id, f"{device_id}.{_signature(device_id, secret)}"


def verify_device_token(token: str | None, secret: bytes) -> str | None:
    """Returns the device id if the token is intact; otherwise None."""
    if not token or token.count(".") != 1:
        return None
    device_id, signature = token.split(".")
    try:
        if str(UUID(device_id)) != device_id:
            return None
    except ValueError:
        return None
    if not hmac.compare_digest(signature, _signature(device_id, secret)):
        return None
    return device_id
