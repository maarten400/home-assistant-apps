import asyncio
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from settings import enabled


class FetchError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def is_challenge(html):
    text = html.lower()
    return "ct.captcha-delivery.com/c.js" in text or "geo.captcha-delivery.com" in text or "please enable js and disable any ad blocker" in text


class Browser:
    async def start(self):
        from playwright.async_api import async_playwright
        self.closed = True
        self.driver = await async_playwright().start()
        try:
            self.context = await self.driver.chromium.launch_persistent_context(
                os.getenv("BROWSER_PROFILE_DIR", "/data/browser-profile"),
                headless=False,
                chromium_sandbox=enabled("CHROMIUM_SANDBOX"),
                viewport={"width": 1280, "height": 800},
                args=["--disable-dev-shm-usage", "--window-size=1280,900"],
                accept_downloads=False,
                env={k: v for k, v in os.environ.items() if k not in {"API_KEY", "SUPERVISOR_TOKEN"}},
            )
        except Exception:
            await self.driver.stop()
            raise
        self.closed = False
        self.context.on("close", lambda: setattr(self, "closed", True))
        if enabled("BROWSER_SETUP_ENABLED") and enabled("FINN_PERMISSION_CONFIRMED"):
            page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            try:
                await page.goto("https://www.finn.no/realestate/homes/search.html", wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass

    async def close(self):
        try:
            if not self.closed:
                await self.context.close()
        finally:
            await self.driver.stop()

    async def fetch(self, params, meta, directory):
        from playwright.async_api import TimeoutError as BrowserTimeout
        from parser import ParseError, parse_properties
        if self.closed:
            raise FetchError("BROWSER_CLOSED")
        page = None
        tracing = False
        html = ""
        debug = enabled("SAVE_FAILURE_HTML")
        try:
            if debug:
                await self.context.tracing.start(screenshots=True, snapshots=True, sources=False)
                tracing = True
            page = await self.context.new_page()
            def response_received(response):
                if response.request.is_navigation_request() and response.frame == page.main_frame:
                    meta["upstream_status"] = response.status
            page.on("response", response_received)
            await page.goto("https://www.finn.no/realestate/homes/search.html?" + urlencode(params), wait_until="domcontentloaded", timeout=25000)
            deadline = time.monotonic() + 20
            while True:
                html = await page.content()
                if len(html.encode()) > 5 * 1024 * 1024:
                    raise FetchError("RESPONSE_TOO_LARGE")
                challenge = is_challenge(html)
                if not challenge:
                    if meta.get("upstream_status", 200) >= 400:
                        raise FetchError("UPSTREAM_HTTP_ERROR")
                    try:
                        return parse_properties(html)
                    except ParseError:
                        pass
                if time.monotonic() >= deadline:
                    raise FetchError("UPSTREAM_BOT_PROTECTION" if challenge else "PARSE_FAILED")
                await asyncio.sleep(1)
        except Exception as exc:
            if debug and page is not None:
                base = Path(directory) / meta["request_id"]
                try:
                    html = await page.content()
                    base.with_suffix(".html").write_text(html[:5 * 1024 * 1024], encoding="utf-8")
                    await page.screenshot(path=str(base.with_suffix(".png")), timeout=5000)
                    meta["capture_saved"] = True
                except Exception:
                    meta["capture_saved"] = False
                if tracing:
                    try:
                        await self.context.tracing.stop(path=str(base.with_suffix(".zip")))
                    except Exception:
                        pass
                    tracing = False
            if isinstance(exc, FetchError):
                raise
            raise FetchError("BROWSER_TIMEOUT" if isinstance(exc, BrowserTimeout) else "BROWSER_ERROR") from None
        finally:
            if tracing:
                try:
                    await self.context.tracing.stop()
                except Exception:
                    pass
            if page is not None:
                try:
                    await page.close()
                except Exception:
                    pass
