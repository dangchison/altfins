# -*- coding: utf-8 -*-
"""
scraper/drawer_extractor.py

Handles clicking a chart pattern card to open the detail drawer,
navigating to the Indicators tab, and extracting all 5 indicator grids:
  Grid 0 — Leading Indicators (RSI, STOCH, MACD, BB, ADX...)
  Grid 1 — All Time High
  Grid 2 — 52-Week Range
  Grid 3 — Moving Averages
  Grid 4 — Performance / Volume

Only called for CHART_PATTERN source — the drawer is not present on
Market Highlights in the same interactive way.
"""
from __future__ import annotations

import json
from typing import Optional
from pydantic import BaseModel
from src.logger import get_logger

log = get_logger(__name__)


class DrawerExtraction(BaseModel):
    """All indicator fields extracted from the Indicators tab drawer."""

    # Grid 4 — Performance / Volume
    volume: str = "N/A"
    volume_usd: str = "N/A"
    vwma: str = "N/A"
    price_high: str = "N/A"
    price_low: str = "N/A"
    change_1d: str = "N/A"
    change_1w: str = "N/A"
    change_1m: str = "N/A"
    change_3m: str = "N/A"
    change_6m: str = "N/A"
    change_1y: str = "N/A"
    change_ytd: str = "N/A"

    # Grid 0 — Leading Indicators
    unusual_volume: str = "N/A"
    rsi_14: str = "N/A"
    rsi_divergence: str = "N/A"
    stoch_rsi: str = "N/A"
    stoch_rsi_k: str = "N/A"
    cci_20: str = "N/A"
    williams: str = "N/A"
    macd_signal: str = "N/A"
    adx_signal: str = "N/A"
    bb_upper: str = "N/A"
    bb_lower: str = "N/A"
    bb_cross_upper: str = "N/A"
    bb_cross_lower: str = "N/A"

    # Grid 1 — All-Time High
    ath_price: str = "N/A"
    ath_date: str = "N/A"
    pct_from_ath: str = "N/A"
    days_from_ath: str = "N/A"

    # Grid 2 — 52-Week Range
    week52_high: str = "N/A"
    week52_low: str = "N/A"
    pct_from_52w_high: str = "N/A"
    pct_above_52w_low: str = "N/A"

    # Grid 3 — Moving Averages (key ones + full JSON)
    sma_20_trend: str = "N/A"
    sma_50_trend: str = "N/A"
    sma_200_trend: str = "N/A"
    ema_9_trend: str = "N/A"
    ema_26_trend: str = "N/A"
    ma_summary: str = "N/A"

    # Trend Scorecard (altfins-scorecard shadow DOM)
    s_trend: str = "N/A"      # Short-Term Trend (e.g. "Up (8/10)")
    m_trend: str = "N/A"      # Medium-Term Trend (e.g. "Strong Up (10/10)")
    l_trend: str = "N/A"      # Long-Term Trend (e.g. "Down (3/10)")


# ---------------------------------------------------------------------------
# JS extraction script — runs inside the browser after drawer + tab are open
# ---------------------------------------------------------------------------
_DRAWER_SCRIPT = """() => {
    const result = {};

    // Helper: build a label→value dict from a flat cell array.
    // Cells alternate [label, value, label, value, ...]; skip header rows.
    const cellsToDict = (cells) => {
        const d = {};
        for (let i = 0; i < cells.length - 1; i += 2) {
            const k = cells[i]?.trim();
            const v = cells[i + 1]?.trim();
            if (k && k !== 'Col0' && k !== 'Col1') d[k] = v ?? 'N/A';
        }
        return d;
    };

    // Helper: build dict from a 3-column MA grid [label, trend, value%]
    const maGridToDict = (cells) => {
        const d = {};
        // First 3 cells are headers (Moving Average | Trend | Value), skip
        for (let i = 3; i < cells.length - 1; i += 3) {
            const label = cells[i]?.trim();
            const trend = cells[i + 1]?.trim();
            const value = cells[i + 2]?.trim();
            if (label && label !== 'Moving Average') {
                d[label] = { trend: trend ?? 'N/A', value: value ?? 'N/A' };
            }
        }
        return d;
    };

    // Collect all vaadin-grids and their cell text
    const grids = Array.from(document.querySelectorAll('vaadin-grid'));
    const gridCells = grids.map(g =>
        Array.from(g.querySelectorAll('vaadin-grid-cell-content'))
            .map(c => c.innerText?.trim() ?? '')
            .filter(t => t.length > 0)
    );

    result.gridCount = gridCells.length;

    // --- Grid 0: Leading Indicators (oscillators, BB, volume spike)
    // Structure: pairs [label, value] OR [label, trend] with occasional 3-col rows
    // We use a label-lookup approach on the flat cell list.
    if (gridCells[0]) {
        const cells = gridCells[0];
        // Build simple label→next-cell dict
        const d = {};
        for (let i = 0; i < cells.length - 1; i++) {
            const k = cells[i]?.trim();
            if (k && k.length > 1) {
                // Peek next cell — if it looks like a value/trend (not a label), map it
                const next = cells[i + 1]?.trim();
                if (next && !next.includes('RSI') && !next.includes('STOCH') &&
                    !next.includes('Bollinger') && !next.includes('Price cross') &&
                    !next.includes('ADX') && !next.includes('MACD') &&
                    !next.includes('Williams') && !next.includes('CCI') &&
                    !next.includes('MOM') && !next.includes('Oscillator') &&
                    !next.includes('Unusual')) {
                    d[k] = next;
                }
            }
        }
        result.grid0 = d;

        // Specifically extract Unusual Volume Spike (may be "Yes" or "-")
        const uvIdx = cells.findIndex(c => c === 'Unusual Volume Spike');
        result.unusualVolume = uvIdx >= 0 ? (cells[uvIdx + 1] ?? 'N/A') : 'N/A';

        // RSI 14
        const rsi14Idx = cells.findIndex(c => c === 'RSI 14');
        result.rsi14 = rsi14Idx >= 0 ? (cells[rsi14Idx + 1] ?? 'N/A') : 'N/A';

        // RSI Divergence
        const rsiDivIdx = cells.findIndex(c => c === 'RSI Divergence');
        result.rsiDivergence = rsiDivIdx >= 0 ? (cells[rsiDivIdx + 1] ?? 'N/A') : 'N/A';

        // Stochastic RSI Fast
        const stochFastIdx = cells.findIndex(c => c === 'Stochastic RSI Fast');
        result.stochRsi = stochFastIdx >= 0 ? (cells[stochFastIdx + 1] ?? 'N/A') : 'N/A';

        // Stochastic RSI (K) value
        const stochKIdx = cells.findIndex(c => c === 'Stochastic RSI (K)');
        result.stochRsiK = stochKIdx >= 0 ? (cells[stochKIdx + 1] ?? 'N/A') : 'N/A';

        // CCI 20
        const cciIdx = cells.findIndex(c => c === 'CCI 20');
        result.cci20 = cciIdx >= 0 ? (cells[cciIdx + 1] ?? 'N/A') : 'N/A';

        // Williams
        const wilIdx = cells.findIndex(c => c === 'Williams');
        result.williams = wilIdx >= 0 ? (cells[wilIdx + 1] ?? 'N/A') : 'N/A';

        // MACD
        const macdIdx = cells.findIndex(c => c === 'MACD');
        result.macd = macdIdx >= 0 ? (cells[macdIdx + 1] ?? 'N/A') : 'N/A';

        // ADX
        const adxIdx = cells.findIndex(c => c === 'ADX');
        result.adx = adxIdx >= 0 ? (cells[adxIdx + 1] ?? 'N/A') : 'N/A';

        // Bollinger Bands
        const bbUpperIdx = cells.findIndex(c => c === 'Upper Bollinger Band');
        result.bbUpper = bbUpperIdx >= 0 ? (cells[bbUpperIdx + 1] ?? 'N/A') : 'N/A';

        const bbLowerIdx = cells.findIndex(c => c === 'Lower Bollinger Band');
        result.bbLower = bbLowerIdx >= 0 ? (cells[bbLowerIdx + 1] ?? 'N/A') : 'N/A';

        const bbCrossUpper = cells.findIndex(c => c === 'Price cross Upper Bollinger Band');
        result.bbCrossUpper = bbCrossUpper >= 0 ? (cells[bbCrossUpper + 1] ?? 'N/A') : 'N/A';

        const bbCrossLower = cells.findIndex(c => c === 'Price cross Lower Bollinger Band');
        result.bbCrossLower = bbCrossLower >= 0 ? (cells[bbCrossLower + 1] ?? 'N/A') : 'N/A';
    }

    // --- Grid 1: All-Time High — pairs [label, value], first 2 cells are header
    if (gridCells[1]) {
        const d = cellsToDict(gridCells[1].slice(2));
        result.athPrice = d['All Time High Price ($)'] ?? 'N/A';
        result.athDate = d['ATH Date'] ?? 'N/A';
        result.pctFromAth = d['% Down from ATH'] ?? 'N/A';
        result.daysFromAth = d['Days since ATH'] ?? 'N/A';
    }

    // --- Grid 2: 52-Week Range — pairs [label, value], first 2 cells are header
    if (gridCells[2]) {
        const d = cellsToDict(gridCells[2].slice(2));
        result.week52High = d['52-Week High'] ?? 'N/A';
        result.week52Low = d['52-Week Low'] ?? 'N/A';
        result.pctFrom52wHigh = d['% Down from 52-Week High'] ?? 'N/A';
        result.pctAbove52wLow = d['% Above 52-Week Low'] ?? 'N/A';
    }

    // --- Grid 3: Moving Averages — triplets [label, trend, value%]
    if (gridCells[3]) {
        const maDict = maGridToDict(gridCells[3]);
        result.sma20Trend = maDict['SMA 20 Trend']?.trend ?? 'N/A';
        result.sma50Trend = maDict['SMA 50 Trend']?.trend ?? 'N/A';
        result.sma200Trend = maDict['SMA 200 Trend']?.trend ?? 'N/A';
        result.ema9Trend = maDict['EMA 9 Trend']?.trend ?? 'N/A';
        result.ema26Trend = maDict['EMA 26 Trend']?.trend ?? 'N/A';
        result.maSummary = JSON.stringify(maDict);
    }

    // --- Grid 4: Performance / Volume — pairs [label, value], first 2 cells are header
    if (gridCells[4]) {
        const d = cellsToDict(gridCells[4].slice(2));
        result.volume = d['Volume'] ?? 'N/A';
        result.volumeUsd = d['Volume ($)'] ?? 'N/A';
        result.vwma = d['VWMA'] ?? 'N/A';
        result.priceHigh = d['High'] ?? 'N/A';
        result.priceLow = d['Low'] ?? 'N/A';
        result.change1d = d['1D'] ?? 'N/A';
        result.change1w = d['1W'] ?? 'N/A';
        result.change1m = d['1M'] ?? 'N/A';
        result.change3m = d['3M'] ?? 'N/A';
        result.change6m = d['6M'] ?? 'N/A';
        result.change1y = d['1Y'] ?? 'N/A';
        result.changeYtd = d['YTD'] ?? 'N/A';
    }

    // --- Trend Scorecard (altfins-scorecard shadow DOM)
    // Selectors confirmed: .altfins-scorecard-trend-short/medium/long contain the score text
    const scorecard = document.querySelector('altfins-scorecard');
    if (scorecard && scorecard.shadowRoot) {
        const sr = scorecard.shadowRoot;
        const short = sr.querySelector('.altfins-scorecard-trend-short');
        const medium = sr.querySelector('.altfins-scorecard-trend-medium');
        const long = sr.querySelector('.altfins-scorecard-trend-long');
        result.sTrend = short ? short.innerText.trim() : 'N/A';
        result.mTrend = medium ? medium.innerText.trim() : 'N/A';
        result.lTrend = long ? long.innerText.trim() : 'N/A';
    } else {
        result.sTrend = 'N/A';
        result.mTrend = 'N/A';
        result.lTrend = 'N/A';
    }

    return result;
}"""


def extract_open_drawer_indicators(page, symbol: str) -> Optional[DrawerExtraction]:
    """
    Extract all grid data from an already open drawer.
    Clicks the Indicators tab, waits for grids to render, and extracts data.
    """
    log.info("🔍 Extracting drawer indicators for %s...", symbol)
    try:
        # 1. Wait for the Indicators tab to appear and click it
        page.wait_for_timeout(1500)
        tab_clicked = page.evaluate("""() => {
            const tab = document.querySelector('#mdi_detail_tab_indicators');
            if (tab) { tab.click(); return true; }
            return false;
        }""")

        if not tab_clicked:
            log.warning("Indicators tab not found for %s — drawer may not have opened", symbol)
            return None

        # 2. Wait for grids to render (all 5 grids must be present)
        try:
            page.evaluate("""() => new Promise(resolve => {
                let attempts = 0;
                const check = setInterval(() => {
                    const grids = document.querySelectorAll('vaadin-grid');
                    if (grids.length >= 5 || attempts > 25) {
                        clearInterval(check);
                        resolve();
                    }
                    attempts++;
                }, 200);
            })""")
        except Exception as e:
            log.warning("Grid wait interrupted for %s: %s", symbol, e)

        page.wait_for_timeout(500)

        # 3. Extract all indicator data
        raw = page.evaluate(_DRAWER_SCRIPT)

        log.debug("Raw drawer data for %s: %s", symbol, raw)

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
            # Scorecard — Trend scores
            s_trend=raw.get("sTrend", "N/A"),
            m_trend=raw.get("mTrend", "N/A"),
            l_trend=raw.get("lTrend", "N/A"),
        )

        log.info("✅ Drawer indicators extracted for %s", symbol)
        return extraction

    except Exception as e:
        log.error("Failed to extract drawer indicators for %s: %s", symbol, e)
        return None


def extract_card_indicators(page, symbol: str) -> Optional[DrawerExtraction]:
    """
    Click the card for `symbol` on the Chart Patterns page, open the
    Indicators tab in the drawer, extract all grid data, then close
    the drawer by pressing Escape.

    Returns a DrawerExtraction on success, or None if the card is not
    found / drawer does not open.
    """
    try:
        # 1. Find and click the card matching `symbol`
        clicked = page.evaluate(f"""() => {{
            const comps = Array.from(document.querySelectorAll('altfins-trading-pattern-component'));
            for (const c of comps) {{
                const sr = c.shadowRoot;
                if (!sr) continue;
                // Skip locked cards
                if (sr.querySelector('.upgrade-unlock-container')) continue;
                const wh = c.querySelector('widget-header');
                const primary = wh?.shadowRoot?.querySelector('#primary');
                if (primary && primary.innerText.trim() === '{symbol}') {{
                    c.click();
                    return true;
                }}
            }}
            return false;
        }}""")

        if not clicked:
            log.warning("Card for %s not found or locked — skipping drawer extraction", symbol)
            return None

        return extract_open_drawer_indicators(page, symbol)
    except Exception as e:
        log.error("Failed to extract drawer indicators for %s: %s", symbol, e)
        return None
    finally:
        # Always close the drawer
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception:
            pass
