import base64
from collections.abc import Awaitable, Callable
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from contracts import InspectResult
from url_inspector.domain.antibot import check_antibot_block
from url_inspector.domain.browser_driver import BrowserDriverProtocol
from url_inspector.domain.dom_cleaner import clean_dom_text
from url_inspector.infrastructure.resolver import resolve_safe_ip

SCREENSHOT_BUDGET_BYTES = 800_000
SCREENSHOT_QUALITIES = (80, 70, 60, 50, 40)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Text a person actually sees: skips nodes hidden by computed style, not only by inline style.
VISIBLE_TEXT_JS = """
() => {
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const parts = [];
  while (walker.nextNode()) {
    const el = walker.currentNode.parentElement;
    if (!el) continue;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    const hidden = s.display === 'none' || s.visibility === 'hidden' || parseFloat(s.opacity) === 0
      || parseFloat(s.fontSize) < 1 || r.width === 0 || r.height === 0 || r.right < 0 || r.bottom < 0;
    if (!hidden) parts.push(walker.currentNode.textContent);
  }
  return parts.join(' ');
}
"""


def browser_launch_args(hostname: str, resolved_ip: str, proxy_url: str) -> list[str]:
    base = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    if proxy_url:
        # Chromium skips the proxy for localhost unless told otherwise: "<-loopback>" closes that gap.
        return [*base, f"--proxy-server={proxy_url}", "--proxy-bypass-list=<-loopback>"]
    # Local development only: pins the first host; redirects and sub-resources are not validated.
    return [*base, f"--host-resolver-rules=MAP {hostname} {resolved_ip}"]


async def capture_within_budget(
    capture: Callable[[int], Awaitable[bytes]], budget_bytes: int = SCREENSHOT_BUDGET_BYTES
) -> bytes:
    """Best quality that fits the Visual RAG budget; the smallest attempt if none does."""
    shot = b""
    for quality in SCREENSHOT_QUALITIES:
        shot = await capture(quality)
        if len(shot) <= budget_bytes:
            return shot
    return shot


class PlaywrightBrowserDriver(BrowserDriverProtocol):
    """Headless inspection. In production every browser request leaves through the egress proxy."""

    def __init__(self, proxy_url: str = "") -> None:
        self._proxy_url = proxy_url

    async def inspect(self, url: str, timeout_seconds: float = 6.0) -> InspectResult:
        hostname = urlparse(url).hostname
        if not hostname:
            return InspectResult(final_url=url, is_blocked=True, blocked_reason="invalid_url_host")

        # Behind the proxy the inspector has no DNS of its own; the proxy validates every hop.
        resolved_ip = "" if self._proxy_url else await resolve_safe_ip(hostname)
        args = browser_launch_args(hostname, resolved_ip, self._proxy_url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=args)
            try:
                return await self._inspect_page(browser, url, timeout_seconds)
            finally:
                await browser.close()

    async def _inspect_page(self, browser, url: str, timeout_seconds: float) -> InspectResult:
        context = await browser.new_context(viewport={"width": 1280, "height": 720}, user_agent=USER_AGENT)
        page = await context.new_page()
        try:
            await page.goto(url, timeout=int(timeout_seconds * 1000), wait_until="domcontentloaded")
        except (PlaywrightTimeoutError, PlaywrightError) as err:
            return InspectResult(final_url=url, is_blocked=True, blocked_reason=f"browser_navigation_failed: {type(err).__name__}")

        html = await page.content()
        is_blocked, blocked_reason = check_antibot_block(html, await page.title())
        screenshot = await capture_within_budget(lambda q: page.screenshot(type="jpeg", quality=q))
        return InspectResult(
            dom_text=await _visible_text(page, html),
            final_url=page.url,
            screenshot_b64=base64.b64encode(screenshot).decode("ascii"),
            has_password_field=await page.query_selector("input[type='password']") is not None,
            is_blocked=is_blocked,
            blocked_reason=blocked_reason,
        )


async def _visible_text(page, html: str) -> str:
    try:
        return " ".join((await page.evaluate(VISIBLE_TEXT_JS)).split())
    except PlaywrightError:
        return clean_dom_text(html)  # static fallback when the page blocks script evaluation
