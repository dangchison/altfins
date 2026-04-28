# -*- coding: utf-8 -*-
"""
pipeline.py

Orchestrates the full scrape → parse → persist → notify flow.
Each step is delegated to its own specialist layer.
The pipeline itself contains no business logic — it only coordinates.
"""

import os
from datetime import datetime, timezone
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
from src.scraper.patterns_extractor import extract_patterns
from src.scraper.drawer_extractor import extract_card_indicators
from src.services.binance_service import fetch_volume
from src.models.trade_setup import TradeSetup

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
        
        # 1. Download session from Supabase (if enabled)
        has_session = False
        if settings.use_persistent_session:
            has_session = self._repo.download_file("sessions", "auth_state.json", storage_path)
            if has_session:
                log.info("Downloaded existing session from Supabase.")
            else:
                log.info("No existing session found in Supabase.")
        else:
            log.info("Skipping session download (local mode).")

        # 2. Run scraper
        try:
            # Use storage state only if persistent session is enabled and we have one
            state = storage_path if (settings.use_persistent_session and has_session) else None
            
            with BrowserSession(storage_state=state) as page:
                # Force login if persistent session is disabled OR if we have no session data
                should_force = (not settings.use_persistent_session) or (not has_session)
                did_login = login(page, settings.altfins_account, settings.altfins_password, force=should_force)
                
                # Update local storage state if using persistent sessions
                if settings.use_persistent_session:
                    page.context.storage_state(path=storage_path)
                
                # 2.1 Technical Analysis
                if settings.enable_technical_analysis:
                    self._scrape_technical_analysis(page, settings)

                # 2.2 Chart Patterns
                if settings.enable_chart_patterns:
                    self._scrape_chart_patterns(page, settings)

                # 2.3 Market Highlights
                if settings.enable_market_highlights:
                    self._scrape_market_highlights(page, settings)
                
                # 3. Upload updated session back to Supabase (if enabled and session was updated)
                if settings.use_persistent_session:
                    if did_login or not has_session:
                        self._repo.upload_file("sessions", "auth_state.json", storage_path)
                        log.info("Uploaded updated session to Supabase.")
                    else:
                        log.debug("Session was reused, skipping upload.")
                else:
                    log.info("Skipping session upload (local mode).")

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

    def _scrape_technical_analysis(self, page, settings) -> None:
        log.info("--- Scrape Technical Analysis ---")
        page.goto("https://altfins.com/technical-analysis")
        raw_rows = extract_rows(page, num_rows=settings.technical_analysis_max_rows)
        for i, row in enumerate(raw_rows):
            self._process_row(page, row, row_index=i)

    def _scrape_chart_patterns(self, page, settings) -> None:
        log.info("--- Scrape Chart Patterns ---")
        page.goto("https://altfins.com/chart-patterns")
        extractions = extract_patterns(page, source_type="CHART_PATTERN")
        for ext in extractions:
            log.info("Processing Pattern: %s (%s)", ext.coin, ext.symbol)
            setup = TradeSetup(
                date=datetime.now(timezone.utc).strftime("%b %d, %Y"),
                coin=ext.coin,
                symbol=ext.symbol,
                raw_text=ext.raw_text,
                image_url=ext.image_url,
                source_type="CHART_PATTERN",
                pattern_name=ext.pattern_name,
                status=ext.status,
                interval=ext.interval,
                signal=ext.signal,
                s_trend=ext.trend,
                profit_potential=ext.profit_potential,
                price=ext.price,
                price_change=ext.price_change
            )

            # Enrich with drawer indicator data
            drawer = extract_card_indicators(page, ext.symbol)
            if drawer:
                setup.volume = drawer.volume
                setup.volume_usd = drawer.volume_usd
                setup.vwma = drawer.vwma
                setup.price_high = drawer.price_high
                setup.price_low = drawer.price_low
                setup.change_1d = drawer.change_1d
                setup.change_1w = drawer.change_1w
                setup.change_1m = drawer.change_1m
                setup.change_3m = drawer.change_3m
                setup.change_6m = drawer.change_6m
                setup.change_1y = drawer.change_1y
                setup.change_ytd = drawer.change_ytd
                setup.unusual_volume = drawer.unusual_volume
                setup.rsi_14 = drawer.rsi_14
                setup.rsi_divergence = drawer.rsi_divergence
                setup.stoch_rsi = drawer.stoch_rsi
                setup.stoch_rsi_k = drawer.stoch_rsi_k
                setup.cci_20 = drawer.cci_20
                setup.williams = drawer.williams
                setup.macd_signal = drawer.macd_signal
                setup.adx_signal = drawer.adx_signal
                setup.bb_upper = drawer.bb_upper
                setup.bb_lower = drawer.bb_lower
                setup.bb_cross_upper = drawer.bb_cross_upper
                setup.bb_cross_lower = drawer.bb_cross_lower
                setup.ath_price = drawer.ath_price
                setup.ath_date = drawer.ath_date
                setup.pct_from_ath = drawer.pct_from_ath
                setup.days_from_ath = drawer.days_from_ath
                setup.week52_high = drawer.week52_high
                setup.week52_low = drawer.week52_low
                setup.pct_from_52w_high = drawer.pct_from_52w_high
                setup.pct_above_52w_low = drawer.pct_above_52w_low
                setup.sma_20_trend = drawer.sma_20_trend
                setup.sma_50_trend = drawer.sma_50_trend
                setup.sma_200_trend = drawer.sma_200_trend
                setup.ema_9_trend = drawer.ema_9_trend
                setup.ema_26_trend = drawer.ema_26_trend
                setup.ma_summary = drawer.ma_summary
                setup.s_trend = drawer.s_trend
                setup.m_trend = drawer.m_trend
                setup.l_trend = drawer.l_trend

            # Enrich with Binance multi-timeframe volume (public API, no auth)
            binance = fetch_volume(ext.symbol)
            setup.binance_vol_4h = binance.vol_4h
            setup.binance_vol_1d = binance.vol_1d
            setup.binance_vol_3d = binance.vol_3d
            setup.binance_vol_7d = binance.vol_7d

            self._persist_and_notify(setup)

    def _scrape_market_highlights(self, page, settings) -> None:
        log.info("--- Scrape Market Highlights ---")
        page.goto("https://altfins.com/crypto-markets/crypto-market-highlights")

        today = datetime.now(timezone.utc).strftime("%b %d, %Y")
        extractions = extract_patterns(page, source_type="MARKET_HIGHLIGHT")
        for ext in extractions:
            # Early-exit: skip if symbol already captured as CHART_PATTERN today
            if self._repo.symbol_exists_as_chart_pattern(ext.symbol, today):
                log.info(
                    "⏭ Highlight skip: %s (%s) — already captured as CHART_PATTERN",
                    ext.coin, ext.symbol,
                )
                continue

            log.info("Processing Highlight: %s (%s)", ext.coin, ext.symbol)
            setup = TradeSetup(
                date=today,
                coin=ext.coin,
                symbol=ext.symbol,
                raw_text=ext.raw_text,
                image_url=ext.image_url,
                source_type="MARKET_HIGHLIGHT",
                category=ext.category if ext.category != "N/A" else "Highlights",
                pattern_name=ext.pattern_name,
                status=ext.status,
                interval=ext.interval,
                signal=ext.signal,
                s_trend=ext.trend,
                profit_potential=ext.profit_potential,
                price=ext.price,
                price_change=ext.price_change
            )
            self._persist_and_notify(setup)


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

        log.info("Processing TA: %s (%s) — %s", coin, symbol, date)

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
        setup.source_type = "TECHNICAL_ANALYSIS"
        
        # Enrich with drawer indicator data (drawer was opened by click_inspect_button)
        from src.scraper.drawer_extractor import extract_open_drawer_indicators
        drawer = extract_open_drawer_indicators(page, symbol)
        if drawer:
            setup.volume = drawer.volume
            setup.volume_usd = drawer.volume_usd
            setup.vwma = drawer.vwma
            setup.price_high = drawer.price_high
            setup.price_low = drawer.price_low
            setup.change_1d = drawer.change_1d
            setup.change_1w = drawer.change_1w
            setup.change_1m = drawer.change_1m
            setup.change_3m = drawer.change_3m
            setup.change_6m = drawer.change_6m
            setup.change_1y = drawer.change_1y
            setup.change_ytd = drawer.change_ytd
            setup.unusual_volume = drawer.unusual_volume
            setup.rsi_14 = drawer.rsi_14
            setup.rsi_divergence = drawer.rsi_divergence
            setup.stoch_rsi = drawer.stoch_rsi
            setup.stoch_rsi_k = drawer.stoch_rsi_k
            setup.cci_20 = drawer.cci_20
            setup.williams = drawer.williams
            setup.macd_signal = drawer.macd_signal
            setup.adx_signal = drawer.adx_signal
            setup.bb_upper = drawer.bb_upper
            setup.bb_lower = drawer.bb_lower
            setup.bb_cross_upper = drawer.bb_cross_upper
            setup.bb_cross_lower = drawer.bb_cross_lower
            setup.ath_price = drawer.ath_price
            setup.ath_date = drawer.ath_date
            setup.pct_from_ath = drawer.pct_from_ath
            setup.days_from_ath = drawer.days_from_ath
            setup.week52_high = drawer.week52_high
            setup.week52_low = drawer.week52_low
            setup.pct_from_52w_high = drawer.pct_from_52w_high
            setup.pct_above_52w_low = drawer.pct_above_52w_low
            setup.sma_20_trend = drawer.sma_20_trend
            setup.sma_50_trend = drawer.sma_50_trend
            setup.sma_200_trend = drawer.sma_200_trend
            setup.ema_9_trend = drawer.ema_9_trend
            setup.ema_26_trend = drawer.ema_26_trend
            setup.ma_summary = drawer.ma_summary
            setup.s_trend = drawer.s_trend
            setup.m_trend = drawer.m_trend
            setup.l_trend = drawer.l_trend
        
        self._persist_and_notify(setup)
        close_popup(page)

    def _persist_and_notify(self, setup: TradeSetup) -> None:
        """Centralized persistence and notification logic.

        Deduplication priority: CHART_PATTERN > MARKET_HIGHLIGHT.
        If the same symbol + pattern_name + interval + date already exists under
        a different source_type, the incoming MARKET_HIGHLIGHT entry is skipped
        entirely — no DB insert, no Telegram notification.
        """
        # Cross-source dedup: skip MARKET_HIGHLIGHT if CHART_PATTERN already captured it
        if setup.source_type == "MARKET_HIGHLIGHT":
            cross_id = self._repo.find_cross_source(setup)
            if cross_id:
                log.info(
                    "⏭ Cross-source skip: %s (%s) — pattern '%s' [%s] already exists as CHART_PATTERN",
                    setup.coin, setup.symbol, setup.pattern_name, setup.interval,
                )
                return

        existing_id = self._repo.find(setup)
        if not existing_id:
            log.info("✅ New setup: %s (%s) [%s]", setup.coin, setup.symbol, setup.source_type)
            entry_id = self._repo.create(setup)
            if entry_id:
                self._notify_all(setup)
        else:
            log.info("⏭ Same-source skip: %s (%s) [%s] — already in DB", setup.coin, setup.symbol, setup.source_type)

    def _notify_all(self, setup: TradeSetup) -> None:
        """Fan-out to every registered notifier. Errors are isolated per notifier."""
        log.info("🔔 Delivering alerts to %d notifiers...", len(self._notifiers))
        for notifier in self._notifiers:
            try:
                notifier.send(setup)
            except Exception as exc:
                log.error("Notifier %s failed: %s", type(notifier).__name__, exc)
