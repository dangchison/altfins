# -*- coding: utf-8 -*-
from __future__ import annotations
from playwright.sync_api import Page

from src.logger import get_logger

log = get_logger(__name__)

_LOGIN_URL = "https://altfins.com/login"


def login(page: Page, email: str, password: str) -> None:
    """
    Authenticate on altfins.com using email + password.
    Raises RuntimeError if login cannot be completed.
    """
    page.goto(_LOGIN_URL)

    # Switch to login tab if site opens on registration tab
    sign_in = page.locator(
        "vaadin-horizontal-layout.link-to-tab span.link:text('Sign in')"
    )
    if sign_in.count() > 0:
        sign_in.click()
        log.info("Switched to Sign in tab")

    # Fill credentials — Playwright auto-waits for element to be interactable
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
