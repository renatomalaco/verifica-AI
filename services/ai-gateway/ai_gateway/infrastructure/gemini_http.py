import httpx


async def generate_content(
    base_url: str, api_key: str, model: str, timeout_seconds: float, payload: dict
) -> dict:
    """POSTs one generateContent request; every transport failure becomes a RuntimeError."""
    # The key goes in the header, never the URL, so it does not leak into access logs.
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"Gemini request timed out ({timeout_seconds}s)") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"Gemini HTTP error: {exc}") from exc
    except ValueError as exc:
        raise RuntimeError("Gemini answer is not JSON") from exc
