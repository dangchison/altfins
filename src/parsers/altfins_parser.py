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

def parse(raw_text: str, coin: str, symbol: str, date: str) -> TradeSetup:
    """
    Parse raw popup text from Altfins into a structured TradeSetup model.
    Returns a model with "N/A" defaults for any field that cannot be extracted.
    """
    data: dict = {
        "date": date,
        "coin": coin,
        "symbol": symbol,
        "raw_text": raw_text,
        "image_url": "",  # Filled by the pipeline before calling parse()
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
    Format a TradeSetup into an HTML Telegram message.
    All values are HTML-escaped to prevent parse_mode breakage on < > chars.
    """
    e = {k: html.escape(str(v)) for k, v in setup.model_dump().items()}
    return (
        f"🚀 <b>#{e['coin']}</b> Trade Setup | <i>{e['date']}</i>\n\n"
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


def trend_icon(trend_text: str) -> str:
    """Map Altfins trend values to a colored directional icon."""
    t = trend_text.lower().strip()
    if "strong up" in t:
        return "🟢⬆️"
    if "up" in t:
        return "🟢↗️"
    if "strong down" in t:
        return "🔴⬇️"
    if "down" in t:
        return "🔴↘️"
    return "⚪➡️"  # Neutral / Sideways


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
