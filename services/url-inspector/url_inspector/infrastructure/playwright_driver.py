import base64
from urllib.parse import urlparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from contracts import InspectResult
from url_inspector.domain.browser_driver import BrowserDriverProtocol
from url_inspector.domain.dom_cleaner import clean_dom_text
from url_inspector.domain.antibot import check_antibot_block
from url_inspector.infrastructure.resolver import resolve_safe_ip


class PlaywrightBrowserDriver(BrowserDriverProtocol):
    """Headless page inspection driver using isolated Playwright Chromium with DNS pinning."""

    async def inspect(self, url: str, timeout_seconds: float = 6.0) -> InspectResult:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return InspectResult(
                final_url=url,
                is_blocked=True,
                blocked_reason="invalid_url_host",
            )

        # 1. Safe IP resolution and SSRF audit (raises SsrfBlockedException if invalid)
        resolved_ip = await resolve_safe_ip(hostname)

        # 2. Run Playwright with the DNS pinning flag to prevent DNS rebinding
        browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            f"--host-resolver-rules=MAP {hostname} {resolved_ip}",
        ]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=browser_args)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            )
            page = await context.new_page()

            timeout_ms = int(timeout_seconds * 1000)
            try:
                await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            except (PlaywrightTimeoutError, PlaywrightError) as err:
                await browser.close()
                return InspectResult(
                    final_url=url,
                    is_blocked=True,
                    blocked_reason=f"browser_navigation_failed: {type(err).__name__}",
                )

            final_url = page.url
            title = await page.title()
            html = await page.content()

            # Antibot/WAF detection
            is_blocked, blocked_reason = check_antibot_block(html, title)

            # Sensitive field detection (password)
            password_input = await page.query_selector("input[type='password']")
            has_password_field = password_input is not None

            # DOM cleanup
            cleaned_text = clean_dom_text(html)

            # Compressed JPEG screenshot capture
            screenshot_bytes = await page.screenshot(type="jpeg", quality=65)
            screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")

            await browser.close()

            return InspectResult(
                dom_text=cleaned_text,
                final_url=final_url,
                screenshot_b64=screenshot_b64,
                has_password_field=has_password_field,
                is_blocked=is_blocked,
                blocked_reason=blocked_reason,
            )
