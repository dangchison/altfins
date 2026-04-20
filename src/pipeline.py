# -*- coding: utf-8 -*-
"""
pipeline.py

Orchestrates the full scrape → parse → persist → notify flow.
Each step is delegated to its own specialist layer.
The pipeline itself contains no business logic — it only coordinates.
"""

import os
from src.config import get_settings
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
        settings = get_settings()
        storage_path = "auth_state.json"
        
        log.info("📌 ================= Start =================")
        
        # 1. Download session from Supabase
        has_session = self._repo.download_file("sessions", "auth_state.json", storage_path)
        if has_session:
            log.info("Downloaded existing session from Supabase.")
        else:
            log.info("No existing session found in Supabase.")

        # 2. Run scraper with storage state
        try:
            with BrowserSession(storage_state=storage_path if has_session else None) as page:
                login(page, settings.altfins_account, settings.altfins_password)
                
                # If we logged in successfully, save the state for next time
                page.context.storage_state(path=storage_path)
                
                page.goto(_TARGET_URL)

                # Read all rows before opening any popup
                raw_rows = extract_rows(page, num_rows=settings.num_rows)

                for i, row in enumerate(raw_rows):
                    self._process_row(page, row, row_index=i)
                
                # 3. Upload updated session back to Supabase
                self._repo.upload_file("sessions", "auth_state.json", storage_path)
                log.info("Uploaded updated session to Supabase.")

        except Exception as e:
            log.error("Pipeline failed: %s", e)
            raise
        finally:
            if has_session and os.path.exists(storage_path):
                os.remove(storage_path)

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
        log.info("🔔 Delivering alerts to %d notifiers...", len(self._notifiers))
        for notifier in self._notifiers:
            try:
                notifier.send(setup)
            except Exception as exc:
                log.error("Notifier %s failed: %s", type(notifier).__name__, exc)
