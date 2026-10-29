import os
from urllib.parse import urlparse
from fastapi import FastAPI, Depends, HTTPException, status
from contracts import InspectRequest, InspectResult
from url_inspector.domain.ssrf_shield import assert_public_ip, is_literal_ip, SsrfBlockedException
from url_inspector.domain.browser_driver import BrowserDriverProtocol
from url_inspector.infrastructure.playwright_driver import PlaywrightBrowserDriver

app = FastAPI(
    title="Verifica AI - URL Inspector",
    description="Headless inspection of remote pages with isolation and SSRF protection",
    version="0.1.0",
)

# In production EGRESS_PROXY_URL points to the egress container; empty means local development.
_global_driver = PlaywrightBrowserDriver(proxy_url=os.environ.get("EGRESS_PROXY_URL", ""))


def get_browser_driver() -> BrowserDriverProtocol:
    return _global_driver


@app.get("/health")
async def health():
    return {"status": "ok", "service": "url-inspector"}


@app.post("/inspect", response_model=InspectResult)
async def inspect_url(
    payload: InspectRequest,
    driver: BrowserDriverProtocol = Depends(get_browser_driver),
) -> InspectResult:
    parsed = urlparse(payload.url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HTTP and HTTPS are supported.",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL or missing hostname.",
        )

    try:
        if is_literal_ip(hostname):
            assert_public_ip(hostname)
        result = await driver.inspect(payload.url, timeout_seconds=payload.timeout_seconds)
        return result
    except SsrfBlockedException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSRF bloqueado: {exc}",
        ) from exc
    except Exception as exc:
        # Generic connection/network failures return a result with is_blocked=True
        return InspectResult(
            final_url=payload.url,
            is_blocked=True,
            blocked_reason=f"inspection_error: {str(exc)}",
        )
