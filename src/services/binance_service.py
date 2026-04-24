# -*- coding: utf-8 -*-
"""
services/binance_service.py

Fetches OHLCV (candlestick) data from Binance public REST API.
No API key required — uses unauthenticated public endpoints only.

Volume fields returned:
  vol_4h   — Quote volume (USDT) of the latest 4h candle
  vol_1d   — Quote volume (USDT) of the latest 1d candle
  vol_3d   — Sum of quote volume of last 3 daily candles
  vol_7d   — Sum of quote volume of last 7 daily candles
"""
from __future__ import annotations

import re
import time
from typing import Optional

import requests
from pydantic import BaseModel

from src.logger import get_logger

log = get_logger(__name__)

_BINANCE_BASE = "https://api.binance.com/api/v3/klines"
_REQUEST_TIMEOUT = 10  # seconds


class BinanceVolume(BaseModel):
    """Multi-timeframe volume data from Binance."""
    vol_4h: str = "N/A"    # Quote volume (USD) last 4h candle
    vol_1d: str = "N/A"    # Quote volume (USD) last 1d candle
    vol_3d: str = "N/A"    # Sum of quote volume last 3 daily candles
    vol_7d: str = "N/A"    # Sum of quote volume last 7 daily candles


def _format_volume(value: float) -> str:
    """Format volume number to human-readable string with M/K suffix."""
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.2f}"


def _fetch_klines(symbol_usdt: str, interval: str, limit: int) -> Optional[list]:
    """
    Fetch klines from Binance API.
    Returns list of klines or None on error.
    Each kline: [open_time, open, high, low, close, base_vol, close_time,
                 quote_vol, trades, taker_buy_base, taker_buy_quote, ignore]
    """
    try:
        resp = requests.get(
            _BINANCE_BASE,
            params={"symbol": symbol_usdt, "interval": interval, "limit": limit},
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code == 400:
            # Symbol not found on Binance
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log.warning("Binance API error for %s [%s]: %s", symbol_usdt, interval, e)
        return None


def fetch_volume(symbol: str) -> BinanceVolume:
    """
    Fetch multi-timeframe volume for a coin from Binance public API.

    Args:
        symbol: Coin symbol as used on Altfins (e.g. "PYTH", "EURC", "BTC")

    Returns:
        BinanceVolume with formatted volume strings, or all "N/A" on failure.
    """
    # Build USDT trading pair — Binance uses e.g. PYTHUSDT
    symbol_usdt = f"{symbol.upper()}USDT"
    log.debug("Fetching Binance volume for %s...", symbol_usdt)

    # Fetch 4h — just 1 candle (latest closed candle)
    klines_4h = _fetch_klines(symbol_usdt, "4h", 2)  # 2 to get the last CLOSED candle

    # Fetch 1d — 7 candles for 1d, 3d, 7d rollup
    klines_1d = _fetch_klines(symbol_usdt, "1d", 8)  # 8 to ensure 7 complete candles

    if not klines_4h and not klines_1d:
        log.warning("No Binance data for %s — symbol may not trade against USDT", symbol)
        return BinanceVolume()

    result = BinanceVolume()

    # 4h volume — use index [-2] (second to last = last CLOSED candle)
    if klines_4h and len(klines_4h) >= 2:
        try:
            quote_vol_4h = float(klines_4h[-2][7])  # index 7 = quote asset volume
            result.vol_4h = _format_volume(quote_vol_4h)
        except (IndexError, ValueError) as e:
            log.debug("4h volume parse error for %s: %s", symbol, e)

    # 1d, 3d, 7d volumes from daily klines
    if klines_1d and len(klines_1d) >= 2:
        try:
            # Use [-2] for last closed daily candle ([-1] may still be forming)
            closed_daily = klines_1d[:-1]  # exclude the current (open) candle

            if len(closed_daily) >= 1:
                vol_1d = float(closed_daily[-1][7])
                result.vol_1d = _format_volume(vol_1d)

            if len(closed_daily) >= 3:
                vol_3d = sum(float(k[7]) for k in closed_daily[-3:])
                result.vol_3d = _format_volume(vol_3d)

            if len(closed_daily) >= 7:
                vol_7d = sum(float(k[7]) for k in closed_daily[-7:])
                result.vol_7d = _format_volume(vol_7d)

        except (IndexError, ValueError) as e:
            log.debug("1d/3d/7d volume parse error for %s: %s", symbol, e)

    log.info(
        "📊 Binance volume for %s — 4h: %s | 1d: %s | 3d: %s | 7d: %s",
        symbol, result.vol_4h, result.vol_1d, result.vol_3d, result.vol_7d,
    )
    return result
