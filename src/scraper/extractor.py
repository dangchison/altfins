# -*- coding: utf-8 -*-
from __future__ import annotations

from playwright.sync_api import Page

from src.logger import get_logger
from src.scraper.extraction import RawExtraction

log = get_logger(__name__)

# Column layout of the Vaadin async grid
_NUM_COLUMNS = 9
_COL_DATE    = 1
_COL_SYMBOL  = 2
_COL_COIN    = 3


def extract_rows(page: Page, num_rows: int = 2) -> list[list[str]]:
    """Wait for the Vaadin async grid to render and return num_rows rows."""
    page.wait_for_selector(".nis-async-grid", timeout=15_000)

    # Wait until coin-name cells are populated (JS evaluated in browser)
    page.wait_for_function(
        """([numRows, numCols, colCoin]) => {
            const cells = document.querySelectorAll('vaadin-grid-cell-content');
            if (cells.length < numRows * numCols) return false;
            for (let i = 0; i < numRows; i++) {
                const t = cells[i * numCols + colCoin]?.textContent?.trim();
                if (!t || t === 'Asset Name') return false;
            }
            return true;
        }""",
        arg=[num_rows, _NUM_COLUMNS, _COL_COIN],
        timeout=30_000,
    )

    cells = page.locator("vaadin-grid-cell-content").all()
    rows: list[list[str]] = []
    for i in range(num_rows):
        start = i * _NUM_COLUMNS
        row_data = [
            cells[start + j].inner_text().strip()
            for j in range(_NUM_COLUMNS - 1)
        ]
        rows.append(row_data)

    log.info("Extracted %d rows from grid", len(rows))
    return rows


def click_inspect_button(page: Page, row_index: int) -> None:
    """Click the Inspect button for the given 0-based row."""
    buttons = page.locator(".altfins-inspect-btn").all()
    visible = [b for b in buttons if b.is_visible()]
    visible.sort(key=lambda b: b.bounding_box()["y"])

    if row_index >= len(visible):
        log.error("Inspect button not found for row %d (visible: %d)", row_index + 1, len(visible))
        return

    visible[row_index].scroll_into_view_if_needed()
    visible[row_index].click()

    # Wait for popup — no sleep needed
    page.wait_for_selector(".curated-chart-detail", state="visible", timeout=15_000)
    log.info("Clicked inspect button for row %d", row_index + 1)


def extract_popup(page: Page) -> RawExtraction:
    """Extract text and image URL from the visible popup."""

    # Wait until popup text is substantial (real analysis, not placeholder)
    page.wait_for_function(
        "() => (document.querySelector('.curated-chart-detail')?.textContent?.trim()?.length ?? 0) > 50",
        timeout=15_000,
    )
    raw_text = page.locator(".curated-chart-detail").last.inner_text().strip()
    log.info("Popup text extracted (%d chars)", len(raw_text))

    image_url = ""
    try:
        page.wait_for_function(
            "() => { const imgs = document.querySelectorAll('.fullscreen-image'); if (imgs.length === 0) return false; const img = imgs[imgs.length - 1]; return img && img.src && img.src.length > 0; }",
            timeout=10000,
        )
        img = page.locator(".fullscreen-image").last
        image_url = img.get_attribute("src") or ""
        log.info("Popup image extracted")
    except Exception:
        log.warning("No image found in popup or src was empty")

    return RawExtraction(raw_text=raw_text, image_url=image_url)


def close_popup(page: Page) -> None:
    """Close the active Vaadin dialog popup or expanded row."""
    try:
        # 1. Close ALL dialogs via JS (handles multiple overlays)
        page.evaluate("document.querySelectorAll('vaadin-dialog').forEach(el => el.opened = false)")
        page.evaluate("document.querySelectorAll('vaadin-dialog-overlay').forEach(el => el.opened = false)")
    except Exception:
        pass

    try:
        page.locator("body").press("Escape")
        page.wait_for_selector(".curated-chart-detail", state="hidden", timeout=3_000)
    except Exception:
        # If it doesn't close (e.g. it's an expanded grid row that requires another button click),
        # we just swallow the error. The next extract_popup will use .last to get the latest one.
        log.info("Popup/Row did not close, continuing anyway.")

    # Vaadin grid often needs time to settle
    page.wait_for_timeout(2000)
    log.info("Popup close sequence finished")
