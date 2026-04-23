# -*- coding: utf-8 -*-
"""
repositories/base.py

Abstract repository interface.
Swap the concrete implementation (Supabase → Postgres → SQLite) without
touching any other layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.models.trade_setup import TradeSetup


class BaseRepository(ABC):

    @abstractmethod
    def find(self, setup: TradeSetup) -> Optional[str]:
        """
        Return the existing entry ID if a record matching the setup
        already exists, otherwise return None.
        """

    @abstractmethod
    def find_cross_source(self, setup: TradeSetup) -> Optional[str]:
        """
        Return the existing entry ID if a record with the same symbol,
        pattern_name, interval, and date exists under a DIFFERENT source_type.
        Used to prevent duplicate notifications when the same pattern appears
        on both Chart Patterns and Market Highlights pages.
        """

    @abstractmethod
    def create(self, setup: TradeSetup) -> Optional[str]:
        """
        Insert a new entry and return its ID, or None on failure.
        """

    @abstractmethod
    def update(self, entry_id: str, setup: TradeSetup) -> bool:
        """
        Update contents and image for an existing entry.
        Return True on success, False otherwise.
        """

    @abstractmethod
    def download_file(self, bucket: str, remote_path: str, local_path: str) -> bool:
        """Download a file from storage."""

    @abstractmethod
    def upload_file(self, bucket: str, remote_path: str, local_path: str) -> bool:
        """Upload a file to storage."""
