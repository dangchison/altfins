# -*- coding: utf-8 -*-
"""
altfins_parser.py

Pure-Python parsing and formatting logic.
No HTTP calls, no DB access — easy to unit-test in isolation.
"""

import html
import re

from src.models.trade_setup import TradeSetup


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(raw_text: str, coin: str, symbol: str, date: str, image_url: str = "") -> TradeSetup:
    """
    Parse raw popup text from Altfins into a structured TradeSetup model.
    Returns a model with "N/A" defaults for any field that cannot be extracted.
    """
    data: dict = {
        "date": date,
        "coin": coin,
        "symbol": symbol,
        "raw_text": raw_text,
        "image_url": image_url,
    }

    if not raw_text:
        return TradeSetup(**data)

    data["setup"] = _parse_setup(raw_text)
    data["pattern"] = _parse_pattern(raw_text)
    data.update(_parse_trend(raw_text))
    data.update(_parse_momentum(raw_text))
    data.update(_parse_support_resistance(raw_text))

    return TradeSetup(**data)


def format_telegram_message(setup: TradeSetup) -> str:
    """
    Format a TradeSetup into an HTML Telegram message based on its source.
    """
    e = {k: html.escape(str(v)) for k, v in setup.model_dump().items()}

    # Common Link
    binance_link = f"<a href=\"https://www.binance.com/trade/{e['symbol']}_USDT\">#{e['symbol']}</a>"

    if setup.source_type == "TECHNICAL_ANALYSIS":
        return (
            f"🚀 <b>{binance_link}</b> Technical Analysis | <i>{e['date']}</i>\n\n"
            f"📝 <b>Setup:</b> {e['setup']}\n"
            f"📊 <b>Pattern:</b> {e['pattern']}\n"
            f"📈 <b>Trend:</b> "
            f"S {trend_icon(setup.s_trend)} | "
            f"M {trend_icon(setup.m_trend)} | "
            f"L {trend_icon(setup.l_trend)}\n"
            f"⏱ <b>Momentum:</b> {momentum_icon(setup.momentum)} {e['momentum']}\n"
            f"⚡ <b>RSI:</b> {e['rsi']}\n"
            f"🛡 <b>Support:</b> {e['support']}\n"
            f"⚔️ <b>Resistance:</b> {e['resistance']}"
        )

    if setup.source_type == "MARKET_HIGHLIGHT":
        return (
            f"⭐ <b>MARKET HIGHLIGHT ({e['category']}): {binance_link}</b>\n"
            f"💰 <b>Price:</b> {e['price']} (<i>{e['price_change']}</i>)\n\n"
            f"🟢 <b>Status:</b> {e['status']}\n"
            f"📉 <b>Pattern:</b> {e['pattern_name']}\n"
            f"⏱ <b>Interval:</b> {e['interval']}\n"
            f"📊 <b>Signal:</b> {e['signal']}\n"
            f"📈 <b>Trend:</b> {e['s_trend']}\n"
            f"🎯 <b>Profit Potential:</b> <b>{e['profit_potential']}</b>\n\n"
            f"📝 <b>Analysis:</b>\n"
            f"<i>{e['raw_text']}</i>"
        )

    # -----------------------------------------------------------------------
    # CHART_PATTERN — full indicator enriched message
    # -----------------------------------------------------------------------
    def _val(field: str) -> str:
        """Return field value or '—' if N/A."""
        v = e.get(field, "N/A")
        return "—" if v == "N/A" else v

    def _pct(field: str) -> str:
        """Format % change: prepend + if positive, skip if N/A."""
        v = e.get(field, "N/A")
        if v == "N/A" or v == "—":
            return "—"
        return v if v.startswith("-") or v.startswith("+") else f"+{v}"

    def _signal_icon(val: str) -> str:
        t = val.lower()
        if "bullish" in t or "up" in t or "buy" in t:
            return "🟢"
        if "bearish" in t or "down" in t or "sell" in t:
            return "🔴"
        if "overbought" in t:
            return "⚠️"
        if "oversold" in t:
            return "✅"
        return "⚪"

    # Trend score line
    s = _val("s_trend")
    m = _val("m_trend")
    l = _val("l_trend")
    trend_line = (
        f"  {trend_icon(setup.s_trend)} <b>Short:</b> {s}\n"
        f"  {trend_icon(setup.m_trend)} <b>Mid:</b>   {m}\n"
        f"  {trend_icon(setup.l_trend)} <b>Long:</b>  {l}"
    )

    # BB cross alert (only show if Yes)
    bb_alerts = []
    if _val("bb_cross_upper") == "Yes":
        bb_alerts.append("⚡ Price crossed Upper BB")
    if _val("bb_cross_lower") == "Yes":
        bb_alerts.append("⚡ Price crossed Lower BB")
    bb_alert_line = "\n".join(bb_alerts) + "\n" if bb_alerts else ""

    # % change summary (one per line)
    change_parts = []
    for label, field in [("1D", "change_1d"), ("1W", "change_1w"), ("1M", "change_1m"), ("3M", "change_3m")]:
        v = _pct(field)
        change_parts.append(f"  {label}: {v}")
    change_line = "\n".join(change_parts)

    # 52W context
    w52_pct = _val("pct_from_52w_high")
    ath_pct = _val("pct_from_ath")
    context_line = ""
    if w52_pct != "—" or ath_pct != "—":
        context_line = (
            f"\n📅 <b>52W High:</b> {_val('week52_high')} ({w52_pct} from high)\n"
            f"🏆 <b>ATH:</b> {ath_pct} down"
        )

    return (
        f"📐 <b>CHART PATTERN: {binance_link}</b>\n"
        f"💰 <b>Price:</b> {_val('price')} (<i>{_val('price_change')}</i>)  "
        f"H: {_val('price_high')} / L: {_val('price_low')}\n\n"
        # Pattern core
        f"🟢 <b>Status:</b> {_val('status')}\n"
        f"📉 <b>Pattern:</b> {_val('pattern_name')}\n"
        f"⏱ <b>Interval:</b> {_val('interval')}\n"
        f"📊 <b>Signal:</b> {_val('signal')}\n"
        f"🎯 <b>Profit Potential:</b> <b>{_val('profit_potential')}</b>\n\n"
        # Trend scores
        f"📈 <b>Trend Scores:</b>\n{trend_line}\n\n"
        # Key indicators
        f"🔬 <b>Indicators:</b>\n"
        f"  RSI14: {_signal_icon(_val('rsi_14'))} {_val('rsi_14')}  "
        f"| Divergence: {_val('rsi_divergence')}\n"
        f"  MACD: {_signal_icon(_val('macd_signal'))} {_val('macd_signal')}  "
        f"| ADX: {_val('adx_signal')}\n"
        f"  StochRSI: {_signal_icon(_val('stoch_rsi'))} {_val('stoch_rsi')} ({_val('stoch_rsi_k')})\n"
        f"  BB: ↑{_val('bb_upper')} / ↓{_val('bb_lower')}\n"
        f"{bb_alert_line}"
        # Volume — Altfins (24h snapshot) + Binance multi-timeframe
        f"\n📦 <b>Volume (Altfins 24h):</b> {_val('volume')}  (<b>${_val('volume_usd')}</b>)\n"
        f"  Unusual Spike: {_val('unusual_volume')}\n"
        f"  VWMA: {_val('vwma')}\n"
        f"\n📊 <b>Volume (Binance):</b>\n"
        f"  4h: <b>{_val('binance_vol_4h')}</b>\n"
        f"  1d: <b>{_val('binance_vol_1d')}</b>\n"
        f"  3d: <b>{_val('binance_vol_3d')}</b>\n"
        f"  7d: <b>{_val('binance_vol_7d')}</b>\n"
        # Price % changes
        f"\n⏳ <b>Price Change:</b>\n{change_line}\n"
        # 52W / ATH context
        f"{context_line}\n\n"
        # Analysis
        f"📝 <b>Analysis:</b>\n"
        f"<i>{_val('raw_text')}</i>"
    )




def trend_icon(trend_text: str) -> str:
    """Map Altfins trend values to a colored directional icon with text label."""
    t = trend_text.lower().strip()
    if "strong up" in t:
        return "🟢⬆ Strong Up"
    if "up" in t:
        return "🟢↑ Up"
    if "strong down" in t:
        return "🔴⬇ Strong Down"
    if "down" in t:
        return "🔴↓ Down"
    return "⚪→ Neutral"  # Neutral / Sideways


def momentum_icon(momentum_text: str) -> str:
    """Map Altfins momentum keywords to a signal icon."""
    t = momentum_text.lower()
    if "strongly bullish" in t:
        return "✅"
    if "bullish" in t and "inflect" in t:
        return "⚠️"
    if "bullish" in t:
        return "📈"
    if "strongly bearish" in t:
        return "🔴"
    if "bearish" in t and "inflect" in t:
        return "👀"
    if "bearish" in t:
        return "📉"
    return ""


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_setup(raw: str) -> str:
    match = re.search(
        r"Trade setup:\s*(.*?)(?=\nPattern:|$)", raw, re.IGNORECASE | re.DOTALL
    )
    if not match:
        return "N/A"

    text = match.group(1).strip()
    # Remove Altfins advertising / educational injections
    _noise = [
        r"\(Set a price alert\)\.?",
        r"Learn to trade.*?\.",
        r"We also issued.*?\.",
        r"Read here\.",
        r"Read our research.*?\.",
        r"USDe has a market capitalization.*?USDT\.",
    ]
    for pattern in _noise:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL).strip()

    return text or "N/A"


def _parse_pattern(raw: str) -> str:
    match = re.search(
        r"Pattern:\s*(.*?)(?=\nTrend:|$)", raw, re.IGNORECASE | re.DOTALL
    )
    if not match:
        return "N/A"

    text = match.group(1).strip().split(".")[0]
    text = re.sub(r"Price is trading in a\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Price is\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?i)pattern", "", text).strip()
    return text or "N/A"


def _parse_trend(raw: str) -> dict:
    result = {"s_trend": "N/A", "m_trend": "N/A", "l_trend": "N/A"}
    match = re.search(
        r"Trend:\s*Short-term trend is\s*(.*?),\s*Medium-term trend is\s*(.*?),\s*Long-term trend is\s*(.*?)\.",
        raw,
        re.IGNORECASE,
    )
    if match:
        result["s_trend"] = match.group(1).strip()
        result["m_trend"] = match.group(2).strip()
        result["l_trend"] = match.group(3).strip()
    return result


def _parse_momentum(raw: str) -> dict:
    result = {"momentum": "N/A", "rsi": "N/A"}
    match = re.search(
        r"Momentum(?:\s+is|:)?\s*(.*?)(?=\nSupport and Resistance:|$)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        return result

    mom_full = match.group(1).strip()
    rsi_match = re.search(r"([^.]*RSI.*?(?:\.|$))", mom_full, re.IGNORECASE)

    if rsi_match:
        rsi_text = rsi_match.group(1).strip()
        rsi_range = re.search(r"\([^)]*RSI[^)]*\)", rsi_text, re.IGNORECASE)
        result["rsi"] = rsi_range.group(0).strip() if rsi_range else rsi_text

        pure_mom = mom_full.replace(rsi_match.group(0), "").strip(" ._,;-")
        first_sentence = pure_mom.split(".")[0].strip() if pure_mom else ""
        result["momentum"] = first_sentence.capitalize() if first_sentence else "N/A"
    else:
        result["momentum"] = mom_full.strip(" ._,;-").capitalize() or "N/A"

    return result


def _parse_support_resistance(raw: str) -> dict:
    result = {"support": "N/A", "resistance": "N/A"}

    sr_match = re.search(
        r"Support and Resistance:\s*Nearest Support Zone is\s*(.*?)\.\s*"
        r"Nearest Resistance Zone is\s*(.*?)(?:\n|$)",
        raw,
        re.IGNORECASE | re.DOTALL,
    )
    if sr_match:
        result["support"] = sr_match.group(1).strip().rstrip(".")
        result["resistance"] = sr_match.group(2).strip().rstrip(".")
        return result

    # Fallback: parse separately
    s_match = re.search(r"Nearest Support Zone is\s*(.*?)(?:\n|$)", raw, re.IGNORECASE)
    r_match = re.search(r"Nearest Resistance Zone is\s*(.*?)(?:\n|$)", raw, re.IGNORECASE)
    if s_match:
        result["support"] = s_match.group(1).strip().rstrip(".")
    if r_match:
        result["resistance"] = r_match.group(1).strip().rstrip(".")

    return result
