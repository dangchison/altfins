# -*- coding: utf-8 -*-
"""
services/binance_service.py

Fetches OHLCV (candlestick) data for multi-timeframe volume analysis.
Uses a provider chain with automatic fallback:
  1. Binance  — fastest, most accurate (blocked in some regions: HTTP 451)
  2. Bybit    — globally accessible, no geo-restrictions, free, no auth

Volume fields returned:
  vol_4h   — Quote volume (USDT) of the latest closed 4h candle
  vol_1d   — Quote volume (USDT) of the latest closed 1d candle
  vol_3d   — Sum of quote volume of last 3 closed daily candles
  vol_7d   — Sum of quote volume of last 7 closed daily candles
"""
from __future__ import annotations

from typing import Optional

import requests
from pydantic import BaseModel

from src.logger import get_logger

log = get_logger(__name__)

_REQUEST_TIMEOUT = 10  # seconds
_BINANCE_GLOBAL_BASE = "https://api.binance.com/api/v3/klines"
_BINANCE_US_BASE     = "https://api.binance.us/api/v3/klines"


class BinanceVolume(BaseModel):
    """Multi-timeframe volume data. Name kept for backwards compatibility."""
    vol_4h: str = "N/A"
    vol_1d: str = "N/A"
    vol_3d: str = "N/A"
    vol_7d: str = "N/A"


def _format_volume(value: float) -> str:
    """Format volume number to human-readable string with M/K suffix."""
    if value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if value >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:.2f}"


# ---------------------------------------------------------------------------
# Provider 1: Binance
# Kline format: [open_time, open, high, low, close, base_vol, close_time,
#                quote_vol, trades, taker_buy_base, taker_buy_quote, ignore]
# ---------------------------------------------------------------------------

def _binance_fetch(symbol_usdt: str, interval: str, limit: int,
                   base_url: str = _BINANCE_GLOBAL_BASE) -> Optional[list]:
    """
    Fetch klines from a Binance-compatible API endpoint.
    Returns list of klines, None if symbol not found (400),
    or raises _GeoBlockedError if region-blocked (451).
    """
    try:
        resp = requests.get(
            base_url,
            params={"symbol": symbol_usdt, "interval": interval, "limit": limit},
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code == 400:
            return None          # Symbol not traded on this exchange
        if resp.status_code == 451:
            raise _GeoBlockedError(f"Geo-blocked (451) from {base_url}")
        resp.raise_for_status()
        return resp.json()
    except _GeoBlockedError:
        raise
    except requests.RequestException as e:
        log.debug("Request failed %s [%s]: %s", symbol_usdt, interval, e)
        return None


class _GeoBlockedError(Exception):
    pass


def _parse_binance_klines(klines_4h: Optional[list],
                           klines_1d: Optional[list]) -> BinanceVolume:
    """Parse Binance-format klines into BinanceVolume. Shared by global + US."""
    result = BinanceVolume()
    if klines_4h and len(klines_4h) >= 2:
        try:
            result.vol_4h = _format_volume(float(klines_4h[-2][7]))
        except (IndexError, ValueError):
            pass
    if klines_1d and len(klines_1d) >= 2:
        try:
            closed = klines_1d[:-1]
            if len(closed) >= 1:
                result.vol_1d = _format_volume(float(closed[-1][7]))
            if len(closed) >= 3:
                result.vol_3d = _format_volume(sum(float(k[7]) for k in closed[-3:]))
            if len(closed) >= 7:
                result.vol_7d = _format_volume(sum(float(k[7]) for k in closed[-7:]))
        except (IndexError, ValueError):
            pass
    return result


def _binance_volume(symbol: str) -> Optional[BinanceVolume]:
    """Try Binance global. Returns None on geo-block, BinanceVolume otherwise."""
    symbol_usdt = f"{symbol.upper()}USDT"
    try:
        klines_4h = _binance_fetch(symbol_usdt, "4h", 2)
        klines_1d = _binance_fetch(symbol_usdt, "1d", 8)
    except _GeoBlockedError:
        log.debug("Binance global geo-blocked — trying Binance US")
        return None
    if not klines_4h and not klines_1d:
        return BinanceVolume()  # Symbol not on Binance, skip further providers
    return _parse_binance_klines(klines_4h, klines_1d)


def _binance_us_volume(symbol: str) -> Optional[BinanceVolume]:
    """Try Binance US (api.binance.us). Same format as global, fewer pairs."""
    symbol_usdt = f"{symbol.upper()}USDT"
    try:
        klines_4h = _binance_fetch(symbol_usdt, "4h", 2, base_url=_BINANCE_US_BASE)
        klines_1d = _binance_fetch(symbol_usdt, "1d", 8, base_url=_BINANCE_US_BASE)
    except _GeoBlockedError:
        log.debug("Binance US also geo-blocked — trying Bybit")
        return None
    if not klines_4h and not klines_1d:
        return None  # Not on Binance US, try Bybit
    return _parse_binance_klines(klines_4h, klines_1d)


# ---------------------------------------------------------------------------
# Provider 2: Bybit (fallback — globally accessible, no geo-restriction)
# Kline format: ["startTime", "openPrice", "highPrice", "lowPrice",
#                "closePrice", "volume", "turnover"]
# "turnover" (index 6) = quote volume in USDT
# ---------------------------------------------------------------------------

_BYBIT_INTERVAL_MAP = {
    "4h": "240",   # Bybit uses minutes for intraday
    "1d": "D",
}


def _bybit_fetch(symbol_usdt: str, interval_key: str, limit: int) -> Optional[list]:
    """Fetch klines from Bybit V5 public API."""
    bybit_interval = _BYBIT_INTERVAL_MAP.get(interval_key)
    if not bybit_interval:
        return None
    try:
        resp = requests.get(
            "https://api.bybit.com/v5/market/kline",
            params={
                "category": "spot",
                "symbol": symbol_usdt,
                "interval": bybit_interval,
                "limit": limit,
            },
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        # data["result"]["list"] — rows in REVERSE chronological order (newest first)
        klines = data.get("result", {}).get("list", [])
        return list(reversed(klines)) if klines else None
    except requests.RequestException as e:
        log.debug("Bybit request failed for %s [%s]: %s", symbol_usdt, interval_key, e)
        return None


def _bybit_volume(symbol: str) -> Optional[BinanceVolume]:
    """Fetch volume from Bybit. Returns BinanceVolume or None on failure."""
    symbol_usdt = f"{symbol.upper()}USDT"

    klines_4h = _bybit_fetch(symbol_usdt, "4h", 3)
    klines_1d = _bybit_fetch(symbol_usdt, "1d", 9)

    if not klines_4h and not klines_1d:
        log.debug("No Bybit data for %s", symbol_usdt)
        return None

    result = BinanceVolume()

    # 4h: index 6 = turnover (quote vol), use [-2] = last CLOSED candle
    if klines_4h and len(klines_4h) >= 2:
        try:
            result.vol_4h = _format_volume(float(klines_4h[-2][6]))
        except (IndexError, ValueError):
            pass

    # 1d / 3d / 7d (exclude [-1] = current forming candle)
    if klines_1d and len(klines_1d) >= 2:
        try:
            closed = klines_1d[:-1]
            if len(closed) >= 1:
                result.vol_1d = _format_volume(float(closed[-1][6]))
            if len(closed) >= 3:
                result.vol_3d = _format_volume(sum(float(k[6]) for k in closed[-3:]))
            if len(closed) >= 7:
                result.vol_7d = _format_volume(sum(float(k[6]) for k in closed[-7:]))
        except (IndexError, ValueError):
            pass

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_volume(symbol: str) -> BinanceVolume:
    """
    Fetch multi-timeframe volume using a 3-provider chain:
      Binance global → Binance US → Bybit

    Args:
        symbol: Coin symbol (e.g. "PYTH", "BTC"). USDT pair built automatically.

    Returns:
        BinanceVolume with formatted strings, or all "N/A" if unavailable.
    """
    # 1. Try Binance global (best coverage; blocked in US/EU)
    result = _binance_volume(symbol)

    # 2. On geo-block (None), try Binance US
    if result is None:
        log.debug("Trying Binance US for %s", symbol)
        result = _binance_us_volume(symbol)

    # 3. Still None → try Bybit (globally accessible)
    if result is None:
        log.debug("Trying Bybit for %s", symbol)
        result = _bybit_volume(symbol) or BinanceVolume()

    if result.vol_1d != "N/A" or result.vol_4h != "N/A":
        log.info("📊 Volume fetched for %s", symbol)
    else:
        log.debug("No volume data for %s from any provider", symbol)

    return result
