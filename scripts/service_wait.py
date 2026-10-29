"""Start-up time varies by machine: poll /health instead of sleeping a fixed time."""

import time

import httpx


def wait_until_healthy(ports: list[int], timeout_seconds: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    pending = set(ports)
    while pending and time.monotonic() < deadline:
        pending = {port for port in pending if not _is_healthy(port)}
        time.sleep(0.25)
    if pending:
        raise RuntimeError(f"services on ports {sorted(pending)} did not start in {timeout_seconds}s")


def _is_healthy(port: int) -> bool:
    try:
        return httpx.get(f"http://127.0.0.1:{port}/health", timeout=1.0).status_code == 200
    except httpx.HTTPError:
        return False
