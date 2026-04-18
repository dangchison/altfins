# -*- coding: utf-8 -*-
"""
tests/test_repository.py

Unit tests for SupabaseRepository.
The Supabase client is mocked — no real network calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.models.trade_setup import TradeSetup
from src.repositories.supabase_repository import SupabaseRepository

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    return MagicMock()


@pytest.fixture
def repo(mock_client):
    with patch("src.repositories.supabase_repository.create_client", return_value=mock_client):
        return SupabaseRepository(url="https://fake.supabase.co", key="fake-key")


@pytest.fixture
def sample_setup():
    return TradeSetup(
        date="Apr 17, 2026",
        coin="Bitcoin",
        symbol="BTC",
        raw_text="Trade setup: BTC is testing resistance.",
        image_url="https://example.com/chart.png",
        setup="BTC is testing resistance",
        pattern="Ascending triangle",
        s_trend="Up",
        m_trend="Strong Up",
        l_trend="Up",
        momentum="Bullish",
        rsi="(RSI > 30 and RSI < 70)",
        support="60000",
        resistance="70000",
    )


# ---------------------------------------------------------------------------
# find()
# ---------------------------------------------------------------------------

class TestFind:

    def test_returns_id_when_entry_exists(self, repo, mock_client):
        mock_client.table.return_value.select.return_value \
            .eq.return_value.eq.return_value.eq.return_value \
            .order.return_value.limit.return_value \
            .execute.return_value.data = [{"id": "abc-123"}]

        result = repo.find("Bitcoin", "BTC", "Apr 17, 2026")
        assert result == "abc-123"

    def test_returns_none_when_not_found(self, repo, mock_client):
        mock_client.table.return_value.select.return_value \
            .eq.return_value.eq.return_value.eq.return_value \
            .order.return_value.limit.return_value \
            .execute.return_value.data = []

        result = repo.find("Bitcoin", "BTC", "Apr 17, 2026")
        assert result is None


# ---------------------------------------------------------------------------
# create()
# ---------------------------------------------------------------------------

class TestCreate:

    def test_returns_id_on_success(self, repo, mock_client, sample_setup):
        mock_client.table.return_value.insert.return_value \
            .execute.return_value.data = [{"id": "new-id"}]

        result = repo.create(sample_setup)
        assert result is not None
        assert isinstance(result, str)

    def test_returns_none_on_failure(self, repo, mock_client, sample_setup):
        mock_client.table.return_value.insert.return_value \
            .execute.return_value.data = []

        result = repo.create(sample_setup)
        assert result is None

    def test_insert_called_with_correct_fields(self, repo, mock_client, sample_setup):
        mock_client.table.return_value.insert.return_value \
            .execute.return_value.data = [{"id": "x"}]

        repo.create(sample_setup)

        insert_call = mock_client.table.return_value.insert.call_args[0][0]
        assert insert_call["coin"] == "Bitcoin"
        assert insert_call["symbol"] == "BTC"
        assert insert_call["date"] == "Apr 17, 2026"
        assert insert_call["contents"] == sample_setup.raw_text
        assert insert_call["image"] == sample_setup.image_url


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------

class TestUpdate:

    def test_returns_true_on_success(self, repo, mock_client, sample_setup):
        mock_client.table.return_value.update.return_value \
            .eq.return_value.execute.return_value.data = [{"id": "abc"}]

        result = repo.update("abc", sample_setup)
        assert result is True

    def test_returns_false_on_failure(self, repo, mock_client, sample_setup):
        mock_client.table.return_value.update.return_value \
            .eq.return_value.execute.return_value.data = []

        result = repo.update("abc", sample_setup)
        assert result is False
