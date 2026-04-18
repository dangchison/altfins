# -*- coding: utf-8 -*-
"""
pipeline.py

Orchestrates the full scrape → parse → persist → notify flow.
Each step is delegated to its own specialist layer.
The pipeline itself contains no business logic — it only coordinates.
"""

from src.config import settings
from src.notifiers.base import BaseNotifier
from src.parsers.altfins_parser import parse
from src.repositories.base import BaseRepository
from src.scraper.auth import login
from src.scraper.driver import create_driver
from src.scraper.extractor import (
    click_inspect_button,
    close_popup,
    extract_popup_image,
    extract_popup_text,
    extract_rows,
)

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
        print("📌 ================= Start =================\n")
        driver = create_driver()
        try:
            login(driver, settings.altfins_account, settings.altfins_password)
            driver.get(_TARGET_URL)

            # Read all rows before opening any popup — grid is stable here
            raw_rows = extract_rows(driver, num_rows=settings.num_rows)

            for i, row in enumerate(raw_rows):
                self._process_row(driver, row, row_index=i)

        finally:
            driver.quit()
            print("\n📌 ================= End =================")

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _process_row(self, driver, row: list[str], row_index: int) -> None:
        # Guard: need at least 4 columns (index, date, symbol, coin)
        if len(row) < 4:
            print(f"⚠️ Skipping incomplete row: {row}")
            return

        date = row[1]
        symbol = row[2]
        coin = row[3]

        if not coin or not symbol or coin == "Asset Name":
            print(f"❌ Invalid coin data: '{coin}' ('{symbol}')")
            return

        print(f"✅ Processing: {coin} ({symbol}) — {date}")

        click_inspect_button(driver, row_index)

        raw_text = extract_popup_text(driver)
        image_url = extract_popup_image(driver)

        if not image_url:
            print(f"⚠️ Skipping {coin} — no image extracted.")
            close_popup(driver)
            return

        setup = parse(raw_text, coin=coin, symbol=symbol, date=date)
        # Attach image_url after parsing (extractor and parser are independent)
        setup = setup.model_copy(update={"image_url": image_url})

        existing_id = self._repo.find(coin, symbol, date)

        if existing_id:
            self._repo.update(existing_id, setup)
            print(f"🔄 Updated: {coin} ({symbol}) on {date}.")
        else:
            self._repo.create(setup)
            print(f"✅ Created: {coin} ({symbol}) on {date}.")
            self._notify_all(setup)

        close_popup(driver)

    def _notify_all(self, setup) -> None:
        """Fan-out to every registered notifier. Errors are isolated per notifier."""
        for notifier in self._notifiers:
            try:
                notifier.send(setup)
            except Exception as exc:
                print(f"❌ Notifier {type(notifier).__name__} failed: {exc}")
