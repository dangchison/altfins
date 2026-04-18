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
    def find(self, coin: str, symbol: str, date: str) -> Optional[str]:
        """
        Return the existing entry ID if a record for (coin, symbol, date)
        already exists, otherwise return None.
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
