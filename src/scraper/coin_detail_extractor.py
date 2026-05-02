# -*- coding: utf-8 -*-
"""
scraper/coin_detail_extractor.py

Navigates to the Altfins coin detail page (/crypto-screener/{slug}) and
extracts the same DrawerExtraction payload that drawer_extractor produces.

Used by the Market Highlights pipeline to enrich each coin card with full
technical indicator data from the dedicated coin page.

URL pattern: https://altfins.com/crypto-screener/{symbol_lower}-{coin_slug}
  e.g.  BTC  / Bitcoin     → /crypto-screener/btc-bitcoin
        KAITO / KAITO       → /crypto-screener/kaito-kaito
        SHIB  / Shiba Inu   → /crypto-screener/shib-shiba-inu
"""
from __future__ import annotations

import re
from typing import Optional

from src.logger import get_logger
from src.scraper.drawer_extractor import DrawerExtraction, _DRAWER_SCRIPT

log = get_logger(__name__)

_BASE_URL = "https://altfins.com/crypto-screener"


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def extract_coin_detail(
    page,
    symbol: str,
    coin: str,
    return_url: Optional[str] = None,
) -> Optional[DrawerExtraction]:
    """
    Navigate to the coin detail page, extract all indicator data, then
    return to `return_url` (Market Highlights page) if provided.

    Args:
        page:       Playwright Page object (must be authenticated).
        symbol:     Ticker symbol (e.g. "BTC", "KAITO").
        coin:       Full coin name (e.g. "Bitcoin", "KAITO").
        return_url: URL to navigate back to after extraction (optional).

    Returns:
        DrawerExtraction on success, None on failure.
    """
    slug = _build_slug(symbol, coin)
    url = f"{_BASE_URL}/{slug}"
    log.info("🌐 Navigating to coin detail: %s", url)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        _wait_for_grids(page, symbol)
        result = _extract(page, symbol)
        return result
    except Exception as exc:
        log.error("coin_detail_extractor failed for %s (%s): %s", symbol, slug, exc)
        return None
    finally:
        if return_url:
            try:
                page.goto(return_url, wait_until="domcontentloaded", timeout=20_000)
                page.wait_for_timeout(1500)
            except Exception as nav_err:
                log.warning("Failed to navigate back to %s: %s", return_url, nav_err)


# ──────────────────────────────────────────────────────────────────────────────
# Slug builder
# ──────────────────────────────────────────────────────────────────────────────

def _build_slug(symbol: str, coin: str) -> str:
    """
    Build the URL slug for a coin detail page.

    Examples:
      BTC  / Bitcoin   → btc-bitcoin
      KAITO / KAITO    → kaito-kaito
      SHIB / Shiba Inu → shib-shiba-inu
      XRP  / XRP       → xrp-xrp
    """
    sym = symbol.lower().strip()
    # Normalize coin name: lowercase, replace spaces/special chars with hyphens
    name = coin.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return f"{sym}-{name}"


# ──────────────────────────────────────────────────────────────────────────────
# Wait for grids
# ──────────────────────────────────────────────────────────────────────────────

def _wait_for_grids(page, symbol: str) -> None:
    """Wait until at least 3 vaadin-grids are present or timeout after 10s."""
    try:
        page.evaluate("""() => new Promise(resolve => {
            let attempts = 0;
            const check = setInterval(() => {
                const grids = document.querySelectorAll('vaadin-grid');
                const scorecard = document.querySelector('altfins-scorecard');
                if (grids.length >= 3 || attempts > 50) {
                    clearInterval(check);
                    resolve();
                }
                attempts++;
            }, 200);
        })""")
    except Exception as e:
        log.warning("Grid wait interrupted for %s: %s", symbol, e)

    page.wait_for_timeout(800)


# ──────────────────────────────────────────────────────────────────────────────
# Extraction
# ──────────────────────────────────────────────────────────────────────────────

def _extract(page, symbol: str) -> Optional[DrawerExtraction]:
    """Run the shared drawer extraction script and map results."""
    try:
        raw = page.evaluate(_DRAWER_SCRIPT)
        log.debug("Raw coin detail data for %s: %s", symbol, raw)

        extraction = DrawerExtraction(
            # Grid 4 — Performance
            volume=raw.get("volume", "N/A"),
            volume_usd=raw.get("volumeUsd", "N/A"),
            vwma=raw.get("vwma", "N/A"),
            price_high=raw.get("priceHigh", "N/A"),
            price_low=raw.get("priceLow", "N/A"),
            change_1d=raw.get("change1d", "N/A"),
            change_1w=raw.get("change1w", "N/A"),
            change_1m=raw.get("change1m", "N/A"),
            change_3m=raw.get("change3m", "N/A"),
            change_6m=raw.get("change6m", "N/A"),
            change_1y=raw.get("change1y", "N/A"),
            change_ytd=raw.get("changeYtd", "N/A"),
            # Grid 0 — Leading Indicators
            unusual_volume=raw.get("unusualVolume", "N/A"),
            rsi_14=raw.get("rsi14", "N/A"),
            rsi_divergence=raw.get("rsiDivergence", "N/A"),
            stoch_rsi=raw.get("stochRsi", "N/A"),
            stoch_rsi_k=raw.get("stochRsiK", "N/A"),
            cci_20=raw.get("cci20", "N/A"),
            williams=raw.get("williams", "N/A"),
            macd_signal=raw.get("macd", "N/A"),
            adx_signal=raw.get("adx", "N/A"),
            bb_upper=raw.get("bbUpper", "N/A"),
            bb_lower=raw.get("bbLower", "N/A"),
            bb_cross_upper=raw.get("bbCrossUpper", "N/A"),
            bb_cross_lower=raw.get("bbCrossLower", "N/A"),
            # Grid 1 — ATH
            ath_price=raw.get("athPrice", "N/A"),
            ath_date=raw.get("athDate", "N/A"),
            pct_from_ath=raw.get("pctFromAth", "N/A"),
            days_from_ath=raw.get("daysFromAth", "N/A"),
            # Grid 2 — 52-Week
            week52_high=raw.get("week52High", "N/A"),
            week52_low=raw.get("week52Low", "N/A"),
            pct_from_52w_high=raw.get("pctFrom52wHigh", "N/A"),
            pct_above_52w_low=raw.get("pctAbove52wLow", "N/A"),
            # Grid 3 — Moving Averages
            sma_20_trend=raw.get("sma20Trend", "N/A"),
            sma_50_trend=raw.get("sma50Trend", "N/A"),
            sma_200_trend=raw.get("sma200Trend", "N/A"),
            ema_9_trend=raw.get("ema9Trend", "N/A"),
            ema_26_trend=raw.get("ema26Trend", "N/A"),
            ma_summary=raw.get("maSummary", "N/A"),
            # Scorecard
            s_trend=raw.get("sTrend", "N/A"),
            m_trend=raw.get("mTrend", "N/A"),
            l_trend=raw.get("lTrend", "N/A"),
        )

        grid_count = raw.get("gridCount", 0)
        non_na = sum(
            1 for f in [extraction.rsi_14, extraction.macd_signal, extraction.s_trend]
            if f != "N/A"
        )

        if non_na == 0:
            log.warning(
                "⚠️ Coin detail for %s returned all N/A (gridCount=%d) — possible load failure",
                symbol, grid_count,
            )
            return None

        log.info("✅ Coin detail extracted for %s (grids=%d)", symbol, grid_count)
        return extraction

    except Exception as exc:
        log.error("Extraction script failed for %s: %s", symbol, exc)
        return None
