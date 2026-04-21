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
from src.utils.retry import with_retry

_TABLE = "crypto_analysis"


class SupabaseRepository(BaseRepository):

    def __init__(self, url: str, key: str) -> None:
        self._client: Client = create_client(url, key)

    # ------------------------------------------------------------------
    # BaseRepository implementation
    # ------------------------------------------------------------------

    @with_retry(max_attempts=3, base_delay=1.0)
    def find(self, setup: TradeSetup) -> Optional[str]:
        response = (
            self._client.table(_TABLE)
            .select("id")
            .eq("symbol", setup.symbol)
            .eq("source_type", setup.source_type)
            .eq("category", setup.category)
            .eq("pattern_name", setup.pattern_name)
            .eq("date", setup.date)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]["id"]
        return None

    @with_retry(max_attempts=3, base_delay=1.0)
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
                "source_type": setup.source_type,
                "category": setup.category,
                "pattern_name": setup.pattern_name,
                "setup": setup.setup,
                "pattern": setup.pattern,
                "interval": setup.interval,
                "status": setup.status,
                "signal": setup.signal,
                "s_trend": setup.s_trend,
                "m_trend": setup.m_trend,
                "l_trend": setup.l_trend,
                "momentum": setup.momentum,
                "rsi": setup.rsi,
                "support": setup.support,
                "resistance": setup.resistance,
                "profit_potential": setup.profit_potential,
                "price": setup.price,
                "price_change": setup.price_change,
                "created_at": now,
                "updated_at": now,
            })
            .execute()
        )
        return new_id if response.data else None

    @with_retry(max_attempts=3, base_delay=1.0)
    def update(self, entry_id: str, setup: TradeSetup) -> bool:
        response = (
            self._client.table(_TABLE)
            .update({
                "contents": setup.raw_text,
                "image": setup.image_url,
                "setup": setup.setup,
                "pattern": setup.pattern,
                "interval": setup.interval,
                "status": setup.status,
                "signal": setup.signal,
                "s_trend": setup.s_trend,
                "m_trend": setup.m_trend,
                "l_trend": setup.l_trend,
                "momentum": setup.momentum,
                "rsi": setup.rsi,
                "support": setup.support,
                "resistance": setup.resistance,
                "profit_potential": setup.profit_potential,
                "price": setup.price,
                "price_change": setup.price_change,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("id", entry_id)
            .execute()
        )
        return len(response.data) > 0

    def download_file(self, bucket: str, remote_path: str, local_path: str) -> bool:
        try:
            with open(local_path, "wb") as f:
                res = self._client.storage.from_(bucket).download(remote_path)
                f.write(res)
            return True
        except Exception as e:
            # Common case: file doesn't exist yet
            return False

    def upload_file(self, bucket: str, remote_path: str, local_path: str) -> bool:
        try:
            with open(local_path, "rb") as f:
                self._client.storage.from_(bucket).upload(
                    path=remote_path,
                    file=f,
                    file_options={"upsert": "true"}
                )
            return True
        except Exception:
            return False
