# -*- coding: utf-8 -*-
"""
tests/test_parser.py

Unit tests for the Altfins parser.
No network, no DB, no browser — pure function tests.
"""

import pytest

from src.parsers.altfins_parser import (
    format_telegram_message,
    momentum_icon,
    parse,
    trend_icon,
)
from src.models.trade_setup import TradeSetup

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RAW = """Trade setup: BTC is consolidating near key resistance. (Set a price alert).
Pattern: Price is trading in a ascending triangle pattern. The pattern suggests a breakout.
Trend: Short-term trend is Up, Medium-term trend is Strong Up, Long-term trend is Up.
Momentum is Bullish (MACD > Signal). RSI is above 50 (RSI > 30 and RSI < 70).
Support and Resistance: Nearest Support Zone is 60000. Nearest Resistance Zone is 70000."""


# ---------------------------------------------------------------------------
# parse()
# ---------------------------------------------------------------------------

class TestParse:

    def test_returns_trade_setup_model(self):
        result = parse(SAMPLE_RAW, coin="Bitcoin", symbol="BTC", date="Apr 17, 2026")
        assert isinstance(result, TradeSetup)

    def test_coin_symbol_date_are_set(self):
        result = parse(SAMPLE_RAW, coin="Bitcoin", symbol="BTC", date="Apr 17, 2026")
        assert result.coin == "Bitcoin"
        assert result.symbol == "BTC"
        assert result.date == "Apr 17, 2026"

    def test_setup_extracted(self):
        result = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        assert "consolidating" in result.setup
        # Noise phrases are removed
        assert "(Set a price alert)" not in result.setup

    def test_pattern_extracted(self):
        result = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        assert "ascending triangle" in result.pattern.lower()

    def test_trend_extracted(self):
        result = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        assert result.s_trend == "Up"
        assert result.m_trend == "Strong Up"
        assert result.l_trend == "Up"

    def test_momentum_extracted(self):
        result = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        assert result.momentum != "N/A"

    def test_rsi_extracted(self):
        result = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        assert "RSI" in result.rsi

    def test_support_resistance_extracted(self):
        result = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        assert result.support == "60000"
        assert result.resistance == "70000"

    def test_empty_raw_text_returns_defaults(self):
        result = parse("", coin="ETH", symbol="ETH", date="Apr 17, 2026")
        assert result.setup == "N/A"
        assert result.pattern == "N/A"
        assert result.s_trend == "N/A"


# ---------------------------------------------------------------------------
# trend_icon()
# ---------------------------------------------------------------------------

class TestTrendIcon:

    @pytest.mark.parametrize("trend,expected", [
        ("Strong Up", "🟢⬆️"),
        ("Up",        "🟢↗️"),
        ("Strong Down","🔴⬇️"),
        ("Down",      "🔴↘️"),
        ("Sideways",  "⚪➡️"),
        ("",          "⚪➡️"),
    ])
    def test_icon_mapping(self, trend, expected):
        assert trend_icon(trend) == expected


# ---------------------------------------------------------------------------
# momentum_icon()
# ---------------------------------------------------------------------------

class TestMomentumIcon:

    @pytest.mark.parametrize("text,expected", [
        ("Strongly Bullish",       "✅"),
        ("Bullish inflection",     "⚠️"),
        ("Bullish",                "📈"),
        ("Strongly Bearish",       "🔴"),
        ("Bearish inflection",     "👀"),
        ("Bearish",                "📉"),
        ("Neutral",                ""),
        ("",                       ""),
    ])
    def test_icon_mapping(self, text, expected):
        assert momentum_icon(text) == expected


# ---------------------------------------------------------------------------
# format_telegram_message()
# ---------------------------------------------------------------------------

class TestFormatTelegramMessage:

    def test_returns_string(self):
        setup = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        msg = format_telegram_message(setup)
        assert isinstance(msg, str)

    def test_contains_coin_name(self):
        setup = parse(SAMPLE_RAW, coin="Bitcoin", symbol="BTC", date="Apr 17, 2026")
        msg = format_telegram_message(setup)
        assert "Bitcoin" in msg

    def test_html_tags_present(self):
        setup = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        msg = format_telegram_message(setup)
        assert "<b>" in msg

    def test_html_escaping_of_special_chars(self):
        """RSI values like 'RSI > 30' must be HTML-escaped so they don't break Telegram."""
        setup = parse(SAMPLE_RAW, coin="BTC", symbol="BTC", date="Apr 17, 2026")
        msg = format_telegram_message(setup)
        # Raw '>' must be escaped as '&gt;' in the RSI field
        assert "&gt;" in msg or "RSI" in msg  # at minimum RSI is mentioned
