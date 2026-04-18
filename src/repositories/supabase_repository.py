# -*- coding: utf-8 -*-
"""
repositories/supabase_repository.py

Supabase implementation of BaseRepository.
All Supabase-specific code is isolated here — nothing else in the codebase
imports from `supabase` directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from supabase import Client, create_client

from src.models.trade_setup import TradeSetup
from src.repositories.base import BaseRepository

_TABLE = "crypto_analysis"


class SupabaseRepository(BaseRepository):

    def __init__(self, url: str, key: str) -> None:
        self._client: Client = create_client(url, key)

    # ------------------------------------------------------------------
    # BaseRepository implementation
    # ------------------------------------------------------------------

    def find(self, coin: str, symbol: str, date: str) -> Optional[str]:
        response = (
            self._client.table(_TABLE)
            .select("id")
            .eq("coin", coin)
            .eq("symbol", symbol)
            .eq("date", date)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]["id"]
        return None

    def create(self, setup: TradeSetup) -> Optional[str]:
        now = datetime.now(timezone.utc).isoformat()
        new_id = str(uuid.uuid4())

        response = (
            self._client.table(_TABLE)
            .insert({
                "id": new_id,
                "date": setup.date,
                "coin": setup.coin,
                "symbol": setup.symbol,
                "contents": setup.raw_text,
                "image": setup.image_url,
                "created_at": now,
                "updated_at": now,
            })
            .execute()
        )
        return new_id if response.data else None

    def update(self, entry_id: str, setup: TradeSetup) -> bool:
        response = (
            self._client.table(_TABLE)
            .update({
                "contents": setup.raw_text,
                "image": setup.image_url,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", entry_id)
            .execute()
        )
        return len(response.data) > 0
