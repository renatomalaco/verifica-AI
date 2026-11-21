import asyncio
import time

import httpx

# On the free tier Google answers 503 (overloaded) in 1-3 s and often answers the same request
# a moment later: try again while the call's own time budget lasts.
RETRY_PAUSE_SECONDS = 0.5
_OVERLOADED = 503


async def generate_content(
    base_url: str, api_key: str, model: str, timeout_seconds: float, payload: dict
) -> dict:
    """POSTs one generateContent request; every failure becomes a RuntimeError.

    `timeout_seconds` bounds the whole call, retries included, so callers' budgets hold."""
    deadline = time.monotonic() + timeout_seconds
    url = f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent"
    # The key goes in the header, never the URL, so it does not leak into access logs.
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}

    response = await _post(url, headers, payload, deadline, timeout_seconds)
    while response.status_code == _OVERLOADED and _time_left(deadline) > RETRY_PAUSE_SECONDS:
        await asyncio.sleep(RETRY_PAUSE_SECONDS)
        response = await _post(url, headers, payload, deadline, timeout_seconds)
    return _json_of(response)


def _time_left(deadline: float) -> float:
    return deadline - time.monotonic()


async def _post(
    url: str, headers: dict, payload: dict, deadline: float, timeout_seconds: float
) -> httpx.Response:
    try:
        async with httpx.AsyncClient(timeout=max(_time_left(deadline), 0.1)) as client:
            return await client.post(url, json=payload, headers=headers)
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"Gemini request timed out ({timeout_seconds}s)") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Gemini HTTP error: {exc}") from exc


def _json_of(response: httpx.Response) -> dict:
    try:
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Gemini HTTP error: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Gemini answer is not JSON") from exc
