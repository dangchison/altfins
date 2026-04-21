# -*- coding: utf-8 -*-
from __future__ import annotations
from playwright.sync_api import Page

from src.logger import get_logger

log = get_logger(__name__)

_LOGIN_URL = "https://altfins.com/login"


def login(page: Page, email: str, password: str, force: bool = False) -> None:
    """
    Authenticate on altfins.com. 
    Skips the login flow if the session is already valid, unless force=True.
    """
    # Check if already logged in (e.g. from loaded storage state)
    if not force and is_logged_in(page):
        log.info("Session is still valid, skipping login flow.")
        return

    perform_full_login(page, email, password)


def is_logged_in(page: Page) -> bool:
    """Check if the current page session is authenticated."""
    try:
        # Navigate to a page that requires login
        page.goto("https://altfins.com/technical-analysis", wait_until="domcontentloaded")
        
        # Wait for either the login form OR the authenticated drawer menu to appear
        # drawer-menu is a good indicator of being logged in
        try:
            # We wait for either the login input or the drawer menu
            page.wait_for_selector("input[name='username'], .nis-drawer-menu", timeout=8000)
        except Exception:
            pass

        # If we see the login input, we are definitely NOT logged in
        if page.locator("input[name='username']").is_visible():
            return False

        # If we see the drawer menu or the URL is not login, and we don't see login input
        return "login" not in page.url and not page.locator("input[name='username']").is_visible()
    except Exception:
        return False


def perform_full_login(page: Page, email: str, password: str) -> None:
    """Execute the full email/password authentication flow."""
    log.info("Performing full login...")
    page.goto(_LOGIN_URL)

    # Switch to login tab if site opens on registration tab
    try:
        page.locator(
            "vaadin-horizontal-layout.link-to-tab span.link:text('Sign in')"
        ).click(timeout=5000)
        log.info("Switched to Sign in tab")
    except Exception:
        pass  # Already on Login tab, or link didn't appear

    # Fill credentials
    page.locator("input[name='username']").fill(email)
    page.locator("input[name='password']").fill(password)
    page.locator("input[name='password']").press("Enter")

    # Wait for redirect away from login page
    try:
        page.wait_for_url(
            lambda url: "login" not in url,
            timeout=15_000,
        )
        log.info("Login successful")
    except Exception as exc:
        raise RuntimeError(f"Login failed — still on login page: {exc}") from exc
