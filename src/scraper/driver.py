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

    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    def __enter__(self) -> Page:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = self._browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        self._page = context.new_page()
        log.info("Browser session started")
        return self._page

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()
        log.info("Browser session closed")
