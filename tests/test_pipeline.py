# -*- coding: utf-8 -*-
"""
tests/test_pipeline.py

Integration tests for ScrapePipeline.
All external dependencies (browser, DB, HTTP) are mocked.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from src.models.trade_setup import TradeSetup
from src.pipeline import ScrapePipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_setup(**kwargs) -> TradeSetup:
    defaults = dict(
        date="Apr 17, 2026",
        coin="Bitcoin",
        symbol="BTC",
        raw_text="Trade setup: BTC consolidating.",
        image_url="https://example.com/chart.png",
    )
    defaults.update(kwargs)
    return TradeSetup(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.find.return_value = None  # New entry by default
    repo.create.return_value = "new-uuid"
    return repo


@pytest.fixture
def mock_notifier():
    return MagicMock()


@pytest.fixture
def pipeline(mock_repo, mock_notifier):
    return ScrapePipeline(repo=mock_repo, notifiers=[mock_notifier])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestScrapePipeline:

    def _patch_scraper(self, num_rows=1):
        """Context manager that patches all scraper functions."""
        row = ["0", "Apr 17, 2026", "BTC", "Bitcoin", "60000", "70000", "+5%", "100M"]

        patches = {
            "create_driver": MagicMock(return_value=MagicMock()),
            "login": MagicMock(),
            "extract_rows": MagicMock(return_value=[row] * num_rows),
            "click_inspect_button": MagicMock(),
            "extract_popup_text": MagicMock(
                return_value="Trade setup: BTC consolidating."
            ),
            "extract_popup_image": MagicMock(
                return_value="https://example.com/chart.png"
            ),
            "close_popup": MagicMock(),
        }
        return patches

    def test_new_entry_triggers_notify(self, pipeline, mock_repo, mock_notifier):
        """When find() returns None (new entry), notifiers must be called."""
        patches = self._patch_scraper()
        with patch.multiple("src.pipeline", **patches):
            mock_repo.find.return_value = None
            pipeline.run()

        mock_repo.create.assert_called_once()
        mock_notifier.send.assert_called_once()

    def test_existing_entry_skips_notify(self, pipeline, mock_repo, mock_notifier):
        """When find() returns an ID (existing entry), notifiers must NOT be called."""
        patches = self._patch_scraper()
        with patch.multiple("src.pipeline", **patches):
            mock_repo.find.return_value = "existing-id"
            pipeline.run()

        mock_repo.update.assert_called_once()
        mock_notifier.send.assert_not_called()

    def test_multiple_rows_processed(self, pipeline, mock_repo, mock_notifier):
        """All extracted rows are processed."""
        patches = self._patch_scraper(num_rows=2)
        with patch.multiple("src.pipeline", **patches):
            mock_repo.find.return_value = None
            pipeline.run()

        assert mock_repo.create.call_count == 2
        assert mock_notifier.send.call_count == 2

    def test_missing_image_skips_row(self, pipeline, mock_repo, mock_notifier):
        """Rows without an image URL are skipped gracefully."""
        patches = self._patch_scraper()
        patches["extract_popup_image"] = MagicMock(return_value="")
        with patch.multiple("src.pipeline", **patches):
            pipeline.run()

        mock_repo.create.assert_not_called()
        mock_notifier.send.assert_not_called()

    def test_notifier_failure_does_not_abort_pipeline(
        self, pipeline, mock_repo, mock_notifier
    ):
        """A notifier exception must not propagate — pipeline continues."""
        mock_notifier.send.side_effect = RuntimeError("Telegram down")
        patches = self._patch_scraper(num_rows=2)
        with patch.multiple("src.pipeline", **patches):
            mock_repo.find.return_value = None
            # Must not raise
            pipeline.run()

        # Both rows were still created despite notifier failure
        assert mock_repo.create.call_count == 2

    def test_driver_quit_called_on_success(self, pipeline):
        """driver.quit() must always be called (via finally block)."""
        mock_driver = MagicMock()
        patches = self._patch_scraper()
        patches["create_driver"] = MagicMock(return_value=mock_driver)
        with patch.multiple("src.pipeline", **patches):
            pipeline.run()

        mock_driver.quit.assert_called_once()

    def test_driver_quit_called_on_exception(self, pipeline):
        """driver.quit() must be called even if login raises."""
        mock_driver = MagicMock()
        patches = self._patch_scraper()
        patches["create_driver"] = MagicMock(return_value=mock_driver)
        patches["login"] = MagicMock(side_effect=RuntimeError("login failed"))
        with patch.multiple("src.pipeline", **patches):
            with pytest.raises(RuntimeError):
                pipeline.run()

        mock_driver.quit.assert_called_once()
