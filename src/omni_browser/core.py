"""Browser session and guarded Playwright helpers. All browser state stays local."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from .security import check_url, check_sensitive_click


DEFAULT_PROFILE = Path(os.environ.get("OMNI_BROWSER_PROFILE", "~/.local/share/omni-browser-harness/profile")).expanduser()


class BrowserHarness:
    def __init__(self, *, profile: Path | None = None, headless: bool | None = None, executable: str | None = None):
        self.profile = Path(profile or DEFAULT_PROFILE).expanduser().resolve()
        self.headless = (os.environ.get("OMNI_BROWSER_HEADLESS", "0") == "1") if headless is None else headless
        self.executable = executable or os.environ.get("OMNI_BROWSER_EXECUTABLE", "")
        self._pw = None
        self.context = None
        self.page = None

    def start(self):
        if self.context:
            return self
        from playwright.sync_api import sync_playwright
        self.profile.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.profile.chmod(0o700)
        except OSError:
            pass
        self._pw = sync_playwright().start()
        exe = self.executable or shutil.which("chromium") or shutil.which("chromium-browser") or shutil.which("google-chrome")
        opts: dict[str, Any] = {"headless": self.headless, "accept_downloads": False}
        if exe:
            opts["executable_path"] = exe
        try:
            self.context = self._pw.chromium.launch_persistent_context(str(self.profile), **opts)
            self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        except Exception:
            self._pw.stop()
            self._pw = None
            raise
        return self

    def close(self):
        if self.context:
            self.context.close()
            self.context = None
        if self._pw:
            self._pw.stop()
            self._pw = None
        self.page = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *args):
        self.close()

    def _ready(self):
        if self.page is None:
            self.start()
        return self.page

    def open(self, url: str) -> dict[str, str]:
        url = check_url(url)
        page = self._ready()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return {"url": page.url, "title": page.title()}

    def snapshot(self, limit: int = 18_000) -> dict[str, str]:
        page = self._ready()
        # Semantic accessibility snapshot is much cheaper than screenshot-based control.
        try:
            tree = page.locator("body").aria_snapshot(timeout=8_000)
        except Exception:
            tree = page.locator("body").inner_text(timeout=8_000)
        return {"url": page.url, "title": page.title(), "snapshot": tree[:max(1000, min(limit, 60000))]}

    def read(self, limit: int = 20_000) -> dict[str, str]:
        page = self._ready()
        return {"url": page.url, "title": page.title(), "text": page.locator("body").inner_text(timeout=10_000)[:max(1000, min(limit,60000))]}

    def click(self, selector: str, confirm: bool = False) -> dict[str, str]:
        check_sensitive_click(selector, confirm)
        page = self._ready()
        page.locator(selector).first.click(timeout=12_000)
        return {"url": page.url, "title": page.title()}

    def fill(self, selector: str, value: str) -> dict[str, str]:
        page = self._ready()
        page.locator(selector).first.fill(value, timeout=12_000)
        return {"selector": selector, "status": "filled", "url": page.url}

    def press(self, selector: str, key: str) -> dict[str, str]:
        page = self._ready()
        page.locator(selector).first.press(key, timeout=12_000)
        return {"selector": selector, "key": key, "url": page.url}

    def select(self, selector: str, value: str) -> dict[str, str]:
        page = self._ready()
        page.locator(selector).first.select_option(value, timeout=12_000)
        return {"selector": selector, "selected": value, "url": page.url}

    def tabs(self) -> dict[str, Any]:
        self._ready()
        return {"tabs": [{"index": i, "url": p.url, "active": p is self.page} for i, p in enumerate(self.context.pages)]}

    def tab_switch(self, index: int) -> dict[str, str]:
        self._ready()
        tabs = self.context.pages
        if index < 0 or index >= len(tabs):
            raise IndexError("Aba inexistente")
        self.page = tabs[index]
        self.page.bring_to_front()
        return {"url": self.page.url, "title": self.page.title()}

    def back(self) -> dict[str, str]:
        page = self._ready()
        page.go_back(wait_until="domcontentloaded", timeout=15_000)
        return {"url": page.url, "title": page.title()}

    def screenshot(self) -> dict[str, str]:
        page = self._ready()
        folder = self.profile.parent / "screenshots"
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Do not allow user-supplied arbitrary filesystem output paths.
        import datetime
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        path = folder / f"browser-{stamp}.png"
        page.screenshot(path=str(path), full_page=False, animations="disabled")
        return {"path": str(path), "url": page.url}
