# -*- coding: utf-8 -*-
"""
services/breakout_signal.py

Breakout Signal Engine — 11-signal scoring model.

Accepts a TradeSetup and computes a structured BreakoutSignal. No I/O.

Scoring rubric (1 point each, max 11):
  ── Momentum & Direction ──────────────────────────────────────────
  1.  Signal = Buy  OR  pattern name contains "Resistance" / "Breakout"
  2.  MACD = Bullish
  3.  RSI 14 ≠ Overbought          (room to continue above resistance)
  4.  Stoch RSI ≠ Overbought
  5.  CCI 20 = Bullish / positive  (momentum confirmation)
  6.  RSI Divergence = Bullish     (early reversal signal — strongest)
  ── Trend Alignment ───────────────────────────────────────────────
  7.  Short-term trend = Up / Strong Up
  8.  Medium-term trend = Up / Strong Up  (breakout more sustainable)
  9.  SMA 20 Up  AND  EMA 9 Up     (short MAs bullishly aligned)
  ── Volume & Proximity ────────────────────────────────────────────
  10. Unusual Volume Spike = Yes  OR  BB cross Upper = Yes
  11. Price within 5% of resistance level  (breakout is imminent)

is_breakout = True  when confidence_score >= BREAKOUT_THRESHOLD (default 5/11 ≈ 45%)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.trade_setup import TradeSetup

# ──────────────────────────────────────────────────────────────────────────────
# Threshold: at least 5 of 11 signals must be positive
# ──────────────────────────────────────────────────────────────────────────────
BREAKOUT_THRESHOLD = 5
MAX_SCORE = 11


# ──────────────────────────────────────────────────────────────────────────────
# Result model
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class BreakoutSignal:
    is_breakout: bool = False
    confidence: int = 0           # 0–100 integer %
    score: int = 0                # raw count of positive signals
    max_score: int = MAX_SCORE
    entry_price: str = "N/A"
    stop_loss: str = "N/A"
    target_price: str = "N/A"
    risk_reward: str = "N/A"
    expected_timeframe: str = "N/A"
    signal_reasons: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def compute_breakout(setup: "TradeSetup") -> BreakoutSignal:
    """
    Evaluate all 11 breakout conditions and return a BreakoutSignal with
    entry / stop / target / R:R levels computed.
    """
    score = 0
    reasons: list[str] = []

    # ── Signal 1: Buy signal or pattern indicates breakout zone ───────────
    sig = (setup.signal or "").lower()
    pat = (setup.pattern_name or "").lower()
    if "buy" in sig or "resistance" in pat or "breakout" in pat:
        score += 1
        reasons.append("✅ Signal Buy / Pattern vào vùng Resistance")

    # ── Signal 2: MACD Bullish ────────────────────────────────────────────
    macd = (setup.macd_signal or "").lower()
    if "bullish" in macd or "buy" in macd:
        score += 1
        reasons.append("✅ MACD Bullish")

    # ── Signal 3: RSI 14 not overbought (room to run) ─────────────────────
    rsi = (setup.rsi_14 or "").lower()
    if rsi not in ("n/a", "") and "overbought" not in rsi:
        score += 1
        reasons.append(f"✅ RSI 14 không overbought ({setup.rsi_14})")
    elif "overbought" in rsi:
        reasons.append("⚠️ RSI 14 overbought — rủi ro đảo chiều sau breakout")

    # ── Signal 4: Stoch RSI not overbought ────────────────────────────────
    stoch = (setup.stoch_rsi or "").lower()
    if stoch not in ("n/a", "") and "overbought" not in stoch:
        score += 1
        reasons.append(f"✅ Stoch RSI không overbought ({setup.stoch_rsi})")
    elif "overbought" in stoch:
        reasons.append("⚠️ Stoch RSI overbought")

    # ── Signal 5: CCI 20 — bullish momentum ───────────────────────────────
    cci = (setup.cci_20 or "").lower()
    if "bullish" in cci or "buy" in cci or "up" in cci:
        score += 1
        reasons.append(f"✅ CCI 20 Bullish ({setup.cci_20})")
    elif cci not in ("n/a", ""):
        reasons.append(f"⚪ CCI 20: {setup.cci_20}")

    # ── Signal 6: RSI Bullish Divergence — early reversal ────────────────
    rsi_div = (setup.rsi_divergence or "").lower()
    if "bullish" in rsi_div:
        score += 1
        reasons.append("✅ RSI Bullish Divergence — tín hiệu đảo chiều sớm")
    elif "bearish" in rsi_div:
        reasons.append("⚠️ RSI Bearish Divergence — cẩn thận false breakout")

    # ── Signal 7: Short-term trend Up ─────────────────────────────────────
    s_trend = (setup.s_trend or "").lower()
    if "strong up" in s_trend or ("up" in s_trend and "down" not in s_trend):
        score += 1
        reasons.append(f"✅ Short-Term Trend: {setup.s_trend}")

    # ── Signal 8: Medium-term trend Up (sustainable breakout) ────────────
    m_trend = (setup.m_trend or "").lower()
    if "strong up" in m_trend or ("up" in m_trend and "down" not in m_trend):
        score += 1
        reasons.append(f"✅ Mid-Term Trend: {setup.m_trend}")

    # ── Signal 9: SMA 20 Up AND EMA 9 Up (MAs aligned) ───────────────────
    sma20 = (setup.sma_20_trend or "").lower()
    ema9  = (setup.ema_9_trend or "").lower()
    if "up" in sma20 and "up" in ema9:
        score += 1
        reasons.append("✅ SMA 20 + EMA 9 đều Up (MAs xếp thuận chiều)")

    # ── Signal 10: Volume spike OR BB cross upper ─────────────────────────
    vol_spike = (setup.unusual_volume or "").lower()
    bb_cross  = (setup.bb_cross_upper or "").lower()
    if "yes" in vol_spike or "yes" in bb_cross:
        score += 1
        if "yes" in vol_spike:
            reasons.append("✅ Unusual Volume Spike xác nhận")
        if "yes" in bb_cross:
            reasons.append("✅ Giá vượt Upper Bollinger Band")

    # ── Signal 11: Price proximity to resistance (within 5%) ─────────────
    price_f = _parse_float(setup.price)
    res_f   = _parse_float(setup.resistance)
    if price_f and res_f and res_f > 0:
        pct_away = (res_f - price_f) / res_f * 100
        if 0 <= pct_away <= 5:
            score += 1
            reasons.append(f"✅ Giá cách resistance chỉ {pct_away:.1f}% — sắp breakout")
        elif pct_away > 5:
            reasons.append(f"⚪ Giá còn cách resistance {pct_away:.1f}%")

    confidence = round(score / MAX_SCORE * 100)
    is_breakout = score >= BREAKOUT_THRESHOLD

    # ── Compute price levels ───────────────────────────────────────────────
    entry, stop, target, rr = _compute_price_levels(setup)
    timeframe = _expected_timeframe(setup)

    return BreakoutSignal(
        is_breakout=is_breakout,
        confidence=confidence,
        score=score,
        max_score=MAX_SCORE,
        entry_price=entry,
        stop_loss=stop,
        target_price=target,
        risk_reward=rr,
        expected_timeframe=timeframe,
        signal_reasons=reasons,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Price level computation
# ──────────────────────────────────────────────────────────────────────────────
def _compute_price_levels(setup: "TradeSetup") -> tuple[str, str, str, str]:
    """Returns (entry, stop_loss, target, risk_reward) as formatted strings."""
    entry_raw  = _pick_entry(setup)
    stop_raw   = _pick_stop(setup, entry_raw)
    target_raw = _pick_target(setup, entry_raw)

    rr = "N/A"
    if entry_raw and stop_raw and target_raw:
        try:
            gain = target_raw - entry_raw
            risk = entry_raw - stop_raw
            if risk > 0:
                rr = f"1:{gain / risk:.1f}"
        except Exception:
            pass

    return _fmt(entry_raw), _fmt(stop_raw), _fmt(target_raw), rr


def _pick_entry(setup: "TradeSetup") -> float | None:
    """Entry = resistance level (the breakout point), fallback BB Upper."""
    for candidate in [setup.resistance, setup.bb_upper]:
        v = _parse_float(candidate)
        if v:
            return v
    return None


def _pick_stop(setup: "TradeSetup", entry: float | None) -> float | None:
    """Stop = BB Lower → support zone → -2% from entry."""
    v = _parse_float(setup.bb_lower)
    if v:
        return v
    s = _parse_float(setup.support)
    if s:
        return s
    if entry:
        return round(entry * 0.98, 6)
    return None


def _pick_target(setup: "TradeSetup", entry: float | None) -> float | None:
    """Target = entry + profit_potential% (from Altfins analysis)."""
    pct = _parse_pct(setup.profit_potential)
    if pct and entry:
        return round(entry * (1 + pct / 100), 6)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Timeframe guidance
# ──────────────────────────────────────────────────────────────────────────────
_INTERVAL_GUIDE: dict[str, str] = {
    "15m": "Chờ nến 15m đóng trên resistance → vào lệnh nến tiếp theo",
    "1h":  "Xác nhận nến 1H đóng trên resistance → vào lệnh 15m",
    "4h":  "Xác nhận nến 4H đóng trên resistance → vào lệnh 15m",
    "1d":  "Xác nhận nến 1D đóng trên resistance → vào lệnh 15m–1H",
    "1w":  "Xác nhận nến 1W đóng trên resistance → vào lệnh 1H–4H",
}

def _expected_timeframe(setup: "TradeSetup") -> str:
    iv = (setup.interval or "").lower().strip()
    return _INTERVAL_GUIDE.get(iv, f"Xác nhận khung {setup.interval or '?'} → vào lệnh 15m")


# ──────────────────────────────────────────────────────────────────────────────
# Numeric helpers
# ──────────────────────────────────────────────────────────────────────────────
def _parse_float(val: str | None) -> float | None:
    if not val or val in ("N/A", "—"):
        return None
    cleaned = val.replace("$", "").replace(",", "").replace("%", "").strip()
    m = re.search(r"[-+]?\d+\.?\d*", cleaned)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def _parse_pct(val: str | None) -> float | None:
    """Parse '+10.65%' or '10.65' → 10.65."""
    if not val or val in ("N/A", "—"):
        return None
    m = re.search(r"[-+]?\d+\.?\d*", val)
    if m:
        try:
            return float(m.group())
        except ValueError:
            return None
    return None


def _fmt(val: float | None) -> str:
    if val is None:
        return "N/A"
    if val >= 1:
        return f"${val:,.4f}".rstrip("0").rstrip(".")
    return f"${val:.6f}".rstrip("0").rstrip(".")
