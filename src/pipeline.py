# -*- coding: utf-8 -*-
"""
pipeline.py

Orchestrates the full scrape → parse → persist → notify flow.
Each step is delegated to its own specialist layer.
The pipeline itself contains no business logic — it only coordinates.
"""

from src.config import settings
from src.logger import get_logger
from src.notifiers.base import BaseNotifier
from src.parsers.altfins_parser import parse
from src.repositories.base import BaseRepository
from src.scraper.auth import login
from src.scraper.driver import BrowserSession
from src.scraper.extractor import (
    _COL_COIN,
    _COL_DATE,
    _COL_SYMBOL,
    click_inspect_button,
    close_popup,
    extract_popup,
    extract_rows,
)

log = get_logger(__name__)

_TARGET_URL = "https://altfins.com/technical-analysis"


class ScrapePipeline:

    def __init__(
        self,
        repo: BaseRepository,
        notifiers: list[BaseNotifier],
    ) -> None:
        self._repo = repo
        self._notifiers = notifiers

    def run(self) -> None:
        log.info("📌 ================= Start =================")
        with BrowserSession() as page:
            login(page, settings.altfins_account, settings.altfins_password)
            page.goto(_TARGET_URL)

            # Read all rows before opening any popup — grid is stable here
            raw_rows = extract_rows(page, num_rows=settings.num_rows)

            for i, row in enumerate(raw_rows):
                self._process_row(page, row, row_index=i)

        log.info("📌 ================= End =================")

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _process_row(self, page, row: list[str], row_index: int) -> None:
        # Guard: need at least 4 columns (index, date, symbol, coin)
        if len(row) < 4:
            log.warning("Skipping incomplete row: %s", row)
            return

        date = row[_COL_DATE]
        symbol = row[_COL_SYMBOL]
        coin = row[_COL_COIN]

        if not coin or not symbol or coin == "Asset Name":
            log.error("Invalid coin data: '%s' ('%s')", coin, symbol)
            return

        log.info("Processing: %s (%s) — %s", coin, symbol, date)

        click_inspect_button(page, row_index)

        extraction = extract_popup(page)

        if not extraction.image_url:
            log.warning("Skipping %s — no image extracted.", coin)
            close_popup(page)
            return

        setup = parse(
            extraction.raw_text,
            coin=coin,
            symbol=symbol,
            date=date,
            image_url=extraction.image_url,
        )

        existing_id = self._repo.find(coin, symbol, date)

        if existing_id:
            self._repo.update(existing_id, setup)
            log.info("🔄 Updated: %s (%s) on %s.", coin, symbol, date)
        else:
            self._repo.create(setup)
            log.info("✅ Created: %s (%s) on %s.", coin, symbol, date)
            self._notify_all(setup)

        close_popup(page)

    def _notify_all(self, setup) -> None:
        """Fan-out to every registered notifier. Errors are isolated per notifier."""
        for notifier in self._notifiers:
            try:
                notifier.send(setup)
            except Exception as exc:
                log.error("Notifier %s failed: %s", type(notifier).__name__, exc)
