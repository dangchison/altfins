# -*- coding: utf-8 -*-
"""
scraper/coin_detail_extractor.py

Navigates to the Altfins coin detail page (/crypto-screener/{slug}) and
extracts technical indicator data.

Grid layout on coin detail page (verified from KAITO page):
  Grid 0 — Analytics: Market Cap, Volume($), 52W High/Low, ATH
  Grid 1 — Oscillators: RSI 9/14/25, STOCH, CCI 20, Williams, MACD, ADX, BB, RSI Divergence
  Grid 2 — Moving Averages: SMA 5/10/20/50/100/200, EMA 9/26
  Grid 3 — Performance: Price, Volume, 1D/1W/1M/3M/6M/1Y changes, VWMA, High, Low

NOTE: There is NO separate "Indicators" tab. All data is on one scrollable page.
Scorecard (short/medium/long trend) is in altfins-scorecard shadow DOM.
"""
from __future__ import annotations

import re
from typing import Optional

from src.logger import get_logger
from src.scraper.drawer_extractor import DrawerExtraction

log = get_logger(__name__)

_BASE_URL = "https://altfins.com/crypto-screener"

# ──────────────────────────────────────────────────────────────────────────────
# Coin detail page extraction script
# Based on real page inspection of https://altfins.com/crypto-screener/kaito-kaito
# ──────────────────────────────────────────────────────────────────────────────
_COIN_DETAIL_SCRIPT = """
() => {
  const r = { gridCount: 0 };

  // Helper: get all non-empty cell texts from a vaadin-grid
  const cells = (grid) => {
    if (!grid) return [];
    return Array.from(grid.querySelectorAll('vaadin-grid-cell-content'))
      .map(c => c.innerText?.trim())
      .filter(t => t && t.length > 0);
  };

  // Column header names to skip when looking for values
  const HEADERS = new Set([
    'Oscillator','Trend','Value','Analytics','Indicators','Moving Average',
    'Signal','Name','Col0','Col1'
  ]);

  // Find value immediately after a label (exact match), skip headers
  const after = (arr, ...labels) => {
    for (const label of labels) {
      const idx = arr.findIndex(t => t.trim() === label);
      if (idx >= 0) {
        for (let j = idx + 1; j < Math.min(idx + 3, arr.length); j++) {
          const v = arr[j].trim();
          if (v && !HEADERS.has(v)) return v;
        }
      }
    }
    return 'N/A';
  };

  const grids = document.querySelectorAll('vaadin-grid');
  r.gridCount = grids.length;

  // ── Grid 0: Analytics [Analytics, Value, Market Cap($), 113M, Volume($), 2.5M,
  //              52-Week High, 2.4205, 52-Week Low, 0.266,
  //              All Time High Price ($), 2.4205, ATH Date, May 29 2025,
  //              % Down from ATH, -80.28%]
  const g0 = cells(grids[0]);
  r.week52High = after(g0, '52-Week High', '52W High');
  r.week52Low  = after(g0, '52-Week Low',  '52W Low');
  r.athPrice   = after(g0, 'All Time High Price ($)', 'ATH Price ($)', 'ATH Price');
  r.athDate    = after(g0, 'ATH Date');
  r.pctFromAth = after(g0, '% Down from ATH', '% from ATH', 'Down from ATH');
  r.volumeUsd  = after(g0, 'Volume ($)', 'Volume (USD)');

  // ── Grid 1: Oscillators [Oscillator, Trend, Value,
  //     RSI 9, Overbought,  RSI 14, Neutral,  RSI 25, Neutral,
  //     STOCH (%K), Overbought,  CCI 20, Neutral,  Williams %R, Neutral,
  //     MACD Level (EMA 9 and EMA 26), Bullish,
  //     Awesome Oscillator, Bullish,  Momentum, Bullish,
  //     ADX Non-Directional, Trending,
  //     Lower Bollinger Band, 0.38162716,  Upper Bollinger Band, 0.55396...,
  //     Price cross Lower Bollinger Band, No,
  //     Price cross Upper Bollinger Band, No,
  //     RSI Divergence, Bullish Divergence,
  //     Unusual Volume Spike, Yes/No]
  const g1 = cells(grids[1]);
  r.rawOsc = g1;

  r.rsi14         = after(g1, 'RSI 14');
  r.stochK        = after(g1, 'STOCH (%K)', 'Stochastic RSI');
  r.cci20         = after(g1, 'CCI 20', 'CCI(20)');
  r.williams      = after(g1, 'Williams %R', 'Williams');
  r.macd          = after(g1, 'MACD Level (EMA 9 and EMA 26)', 'MACD');
  r.adx           = after(g1, 'ADX Non-Directional', 'ADX');
  r.rsiDivergence = after(g1, 'RSI Divergence');
  r.bbLower       = after(g1, 'Lower Bollinger Band');
  r.bbUpper       = after(g1, 'Upper Bollinger Band');
  r.bbCrossLower  = after(g1, 'Price cross Lower Bollinger Band');
  r.bbCrossUpper  = after(g1, 'Price cross Upper Bollinger Band');

  const uvRaw = after(g1, 'Unusual Volume Spike', 'Unusual Volume');
  r.unusualVolume = (uvRaw && uvRaw !== 'N/A' && uvRaw !== '-' && uvRaw !== 'No') ? 'Yes' : 'No';

  // Normalize "-" → "N/A"
  ['rsi14','stochK','cci20','williams','macd','adx','rsiDivergence'].forEach(k => {
    if (!r[k] || r[k] === '-') r[k] = 'N/A';
  });

  // ── Grid 2: Moving Averages [Moving Average, Trend, Value%,
  //     SMA 5, Trend Up, 9.72%,  SMA 10, Trend Up, -0.87%,
  //     SMA 20, Trend Up, 7.04%,  SMA 50, Trend Up, 16.51%,
  //     SMA 100, Trend Up, ...,  SMA 200, Trend Down, ...,
  //     EMA 9, Trend Up, ...,  EMA 26, Trend Up, ...]
  const g2 = cells(grids[2]);
  r.rawMAs = g2;

  const normMA = (v) => {
    if (!v || v === 'N/A') return 'N/A';
    if (v.toLowerCase().includes('up'))   return 'Up';
    if (v.toLowerCase().includes('down')) return 'Down';
    return v;
  };
  r.sma20Trend  = normMA(after(g2, 'SMA 20'));
  r.sma50Trend  = normMA(after(g2, 'SMA 50'));
  r.sma200Trend = normMA(after(g2, 'SMA 200'));
  r.ema9Trend   = normMA(after(g2, 'EMA 9'));
  r.ema26Trend  = normMA(after(g2, 'EMA 26'));

  const ups   = g2.filter(t => t === 'Trend Up').length;
  const downs = g2.filter(t => t === 'Trend Down').length;
  r.maSummary = JSON.stringify({ up: ups, down: downs });

  // ── Grid 3 (or 4): Performance [Indicators, Value,
  //     Price($), 0.47,  Volume, 5.3M,  Volume($), 2.5M,
  //     Price Change(%), 0.37%,
  //     1D, 1.89%,  1W, 17.11%,  1M, 16.57%,
  //     3M, 35.16%,  6M, -54.52%,  1Y, -47.98%,  YTD, -5.82%,
  //     VWMA, 0.439,  High, 0.48,  Low, 0.44]
  const g3 = cells(grids[3] || grids[4]);
  r.volume    = after(g3, 'Volume');
  r.change1d  = after(g3, '1D');
  r.change1w  = after(g3, '1W', '7D');
  r.change1m  = after(g3, '1M', '30D');
  r.change3m  = after(g3, '3M', '90D');
  r.change6m  = after(g3, '6M');
  r.change1y  = after(g3, '1Y');
  r.vwma      = after(g3, 'VWMA');
  r.priceHigh = after(g3, 'High');
  r.priceLow  = after(g3, 'Low');

  // ── Scorecard (altfins-scorecard shadow DOM)
  r.sTrend = 'N/A'; r.mTrend = 'N/A'; r.lTrend = 'N/A';
  const sc = document.querySelector('altfins-scorecard');
  if (sc && sc.shadowRoot) {
    const sr = sc.shadowRoot;
    r.sTrend = sr.querySelector('.altfins-scorecard-trend-short')?.innerText?.trim() || 'N/A';
    r.mTrend = sr.querySelector('.altfins-scorecard-trend-medium')?.innerText?.trim() || 'N/A';
    r.lTrend = sr.querySelector('.altfins-scorecard-trend-long')?.innerText?.trim() || 'N/A';
    if (r.sTrend === 'N/A') {
      r.scorecardDebug = [...new Set(
        Array.from(sr.querySelectorAll('*')).map(e => e.innerText?.trim()).filter(t => t)
      )].slice(0, 15);
    }
  }

  return r;
}
"""


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
    """
    slug = _build_slug(symbol, coin)
    url = f"{_BASE_URL}/{slug}"
    log.info("🌐 Navigating to coin detail: %s", url)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        _wait_for_oscillator_grid(page, symbol)
        return _extract(page, symbol)
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
    BTC / Bitcoin → btc-bitcoin
    KAITO / KAITO → kaito-kaito
    SHIB / Shiba Inu → shib-shiba-inu
    """
    sym = symbol.lower().strip()
    name = coin.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return f"{sym}-{name}"


# ──────────────────────────────────────────────────────────────────────────────
# Wait for oscillators (Grid 1) to render RSI 14 row
# ──────────────────────────────────────────────────────────────────────────────

def _wait_for_oscillator_grid(page, symbol: str) -> None:
    """
    Poll until Grid 1 has 'RSI 14' cell — up to ~15s (75 × 200ms).
    Also requires at least 3 grids to exist.
    """
    try:
        page.evaluate("""() => new Promise(resolve => {
            let attempts = 0;
            const check = setInterval(() => {
                const grids = document.querySelectorAll('vaadin-grid');
                if (grids.length < 2) {
                    if (++attempts > 75) { clearInterval(check); resolve(); }
                    return;
                }
                const g1cells = Array.from(grids[1].querySelectorAll('vaadin-grid-cell-content'))
                    .map(c => c.innerText?.trim()).filter(t => t);
                if (g1cells.some(c => c === 'RSI 14') || attempts > 75) {
                    clearInterval(check); resolve();
                }
                attempts++;
            }, 200);
        })""")
    except Exception as e:
        log.warning("Oscillator grid wait interrupted for %s: %s", symbol, e)
    page.wait_for_timeout(500)


# ──────────────────────────────────────────────────────────────────────────────
# Extraction
# ──────────────────────────────────────────────────────────────────────────────

def _extract(page, symbol: str) -> Optional[DrawerExtraction]:
    """Run the coin-detail extraction script and build a DrawerExtraction."""
    try:
        raw = page.evaluate(_COIN_DETAIL_SCRIPT)

        grid_count = raw.get("gridCount", 0)
        log.debug(
            "Coin detail raw for %s: grids=%d rsi14=%s macd=%s sma20=%s sTrend=%s",
            symbol, grid_count, raw.get("rsi14"), raw.get("macd"),
            raw.get("sma20Trend"), raw.get("sTrend"),
        )

        # Validate — at least one key field must be populated
        key_fields = [raw.get("rsi14"), raw.get("macd"), raw.get("sma20Trend")]
        non_na = sum(1 for f in key_fields if f and f not in ("N/A", ""))

        if non_na == 0:
            log.warning(
                "⚠️ Coin detail for %s: all key fields N/A (gridCount=%d). "
                "rawOsc sample: %s",
                symbol, grid_count,
                str(raw.get("rawOsc", [])[:10]),
            )
            return None

        extraction = DrawerExtraction(
            # Grid 0 — Analytics
            volume_usd=raw.get("volumeUsd", "N/A"),
            week52_high=raw.get("week52High", "N/A"),
            week52_low=raw.get("week52Low", "N/A"),
            ath_price=raw.get("athPrice", "N/A"),
            ath_date=raw.get("athDate", "N/A"),
            pct_from_ath=raw.get("pctFromAth", "N/A"),
            # Grid 1 — Oscillators
            rsi_14=raw.get("rsi14", "N/A"),
            rsi_divergence=raw.get("rsiDivergence", "N/A"),
            stoch_rsi=raw.get("stochK", "N/A"),
            cci_20=raw.get("cci20", "N/A"),
            williams=raw.get("williams", "N/A"),
            macd_signal=raw.get("macd", "N/A"),
            adx_signal=raw.get("adx", "N/A"),
            bb_upper=raw.get("bbUpper", "N/A"),
            bb_lower=raw.get("bbLower", "N/A"),
            bb_cross_upper=raw.get("bbCrossUpper", "N/A"),
            bb_cross_lower=raw.get("bbCrossLower", "N/A"),
            unusual_volume=raw.get("unusualVolume", "N/A"),
            # Grid 2 — Moving Averages
            sma_20_trend=raw.get("sma20Trend", "N/A"),
            sma_50_trend=raw.get("sma50Trend", "N/A"),
            sma_200_trend=raw.get("sma200Trend", "N/A"),
            ema_9_trend=raw.get("ema9Trend", "N/A"),
            ema_26_trend=raw.get("ema26Trend", "N/A"),
            ma_summary=raw.get("maSummary", "N/A"),
            # Grid 3 — Performance
            volume=raw.get("volume", "N/A"),
            change_1d=raw.get("change1d", "N/A"),
            change_1w=raw.get("change1w", "N/A"),
            change_1m=raw.get("change1m", "N/A"),
            change_3m=raw.get("change3m", "N/A"),
            change_6m=raw.get("change6m", "N/A"),
            change_1y=raw.get("change1y", "N/A"),
            vwma=raw.get("vwma", "N/A"),
            price_high=raw.get("priceHigh", "N/A"),
            price_low=raw.get("priceLow", "N/A"),
            # Scorecard
            s_trend=raw.get("sTrend", "N/A"),
            m_trend=raw.get("mTrend", "N/A"),
            l_trend=raw.get("lTrend", "N/A"),
            # Not available on this page
            stoch_rsi_k="N/A",
            change_ytd="N/A",
            pct_from_52w_high="N/A",
            pct_above_52w_low="N/A",
            days_from_ath="N/A",
        )

        log.info(
            "✅ Coin detail for %s: grids=%d RSI=%s MACD=%s SMA20=%s sTrend=%s",
            symbol, grid_count,
            extraction.rsi_14, extraction.macd_signal,
            extraction.sma_20_trend, extraction.s_trend,
        )
        return extraction

    except Exception as exc:
        log.error("Extraction script failed for %s: %s", symbol, exc)
        return None
