# -*- coding: utf-8 -*-
from __future__ import annotations
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

from src.logger import get_logger

log = get_logger(__name__)


class BrowserSession:
    """
    Context manager for a Playwright browser session.

    Usage:
        with BrowserSession() as page:
            page.goto("https://...")
    """

    def __init__(self, storage_state: str | None = None) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None
        self._storage_state = storage_state

    def __enter__(self) -> Page:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context_args = {"viewport": {"width": 1920, "height": 1080}}
        if self._storage_state:
            context_args["storage_state"] = self._storage_state

        context = self._browser.new_context(**context_args)
        self._page = context.new_page()
        log.info("Browser session started (storage_state=%s)", self._storage_state)
        return self._page

    def save_state(self, path: str) -> None:
        """Save current session state to a file."""
        if self._page:
            self._page.context.storage_state(path=path)
            log.info("Storage state saved to %s", path)

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        log.info("Browser session closed")
