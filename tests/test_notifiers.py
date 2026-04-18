# -*- coding: utf-8 -*-
"""
tests/test_notifiers.py

Unit tests for TelegramNotifier.
HTTP calls are mocked — no real Telegram API calls.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from src.models.trade_setup import TradeSetup
from src.notifiers.telegram_notifier import TelegramNotifier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_setup():
    return TradeSetup(
        date="Apr 17, 2026",
        coin="Ethereum",
        symbol="ETH",
        raw_text="Trade setup: ETH is breaking out.",
        image_url="https://example.com/eth_chart.png",
        setup="ETH is breaking out",
        pattern="Bull flag",
        s_trend="Up",
        m_trend="Up",
        l_trend="Strong Up",
        momentum="Bullish",
        rsi="(RSI > 30 and RSI < 70)",
        support="3000",
        resistance="3500",
    )


@pytest.fixture
def notifier():
    return TelegramNotifier(
        token="test-token",
        chat_ids=["-100111", "-100222"],
    )


# ---------------------------------------------------------------------------
# send() — fan-out
# ---------------------------------------------------------------------------

class TestTelegramNotifierSend:

    @pytest.fixture(autouse=True)
    def mock_sleep(self):
        with patch("time.sleep"):
            yield

    def test_sends_to_all_chat_ids(self, notifier, sample_setup):
        """send() must call the Telegram API for every configured chat ID."""
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"ok": True}

            notifier.send(sample_setup)

            # 2 chat IDs × 3 calls each (photo + raw message + formatted message)
            assert mock_post.call_count == 6

    def test_sends_photo_first(self, notifier, sample_setup):
        """sendPhoto must be called before sendMessage for each chat."""
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"ok": True}

            notifier.send(sample_setup)

            first_call_url = mock_post.call_args_list[0][0][0]
            assert "sendPhoto" in first_call_url

    def test_error_logged_but_does_not_raise(self, notifier, sample_setup):
        """A Telegram API error must not raise — it should log and continue."""
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"ok": False, "description": "Bad Request"}

            # Must not raise
            notifier.send(sample_setup)

    def test_network_exception_does_not_raise(self, notifier, sample_setup):
        """A connection error must not propagate out of send()."""
        with patch("requests.post", side_effect=ConnectionError("timeout")):
            notifier.send(sample_setup)  # Should not raise

    def test_single_chat_id(self, sample_setup):
        """Works correctly with a single chat ID."""
        notifier = TelegramNotifier(token="tok", chat_ids=["-100999"])
        with patch("requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"ok": True}
            notifier.send(sample_setup)
            assert mock_post.call_count == 3  # photo + raw + formatted

    def test_no_chat_ids_makes_no_calls(self, sample_setup):
        """With an empty chat_ids list, no HTTP calls are made."""
        notifier = TelegramNotifier(token="tok", chat_ids=[])
        with patch("requests.post") as mock_post:
            notifier.send(sample_setup)
            mock_post.assert_not_called()
