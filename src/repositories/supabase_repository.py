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
    def find_cross_source(self, setup: TradeSetup) -> Optional[str]:
        """Check if the same pattern exists under a different source_type."""
        response = (
            self._client.table(_TABLE)
            .select("id")
            .eq("symbol", setup.symbol)
            .eq("pattern_name", setup.pattern_name)
            .eq("interval", setup.interval)
            .eq("date", setup.date)
            .neq("source_type", setup.source_type)
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
                # Volume & Performance
                "volume": setup.volume,
                "volume_usd": setup.volume_usd,
                "vwma": setup.vwma,
                "price_high": setup.price_high,
                "price_low": setup.price_low,
                "change_1d": setup.change_1d,
                "change_1w": setup.change_1w,
                "change_1m": setup.change_1m,
                "change_3m": setup.change_3m,
                "change_6m": setup.change_6m,
                "change_1y": setup.change_1y,
                "change_ytd": setup.change_ytd,
                # Leading Indicators
                "unusual_volume": setup.unusual_volume,
                "rsi_14": setup.rsi_14,
                "rsi_divergence": setup.rsi_divergence,
                "stoch_rsi": setup.stoch_rsi,
                "stoch_rsi_k": setup.stoch_rsi_k,
                "cci_20": setup.cci_20,
                "williams": setup.williams,
                "macd_signal": setup.macd_signal,
                "adx_signal": setup.adx_signal,
                "bb_upper": setup.bb_upper,
                "bb_lower": setup.bb_lower,
                "bb_cross_upper": setup.bb_cross_upper,
                "bb_cross_lower": setup.bb_cross_lower,
                # All-Time High
                "ath_price": setup.ath_price,
                "ath_date": setup.ath_date,
                "pct_from_ath": setup.pct_from_ath,
                "days_from_ath": setup.days_from_ath,
                # 52-Week Range
                "week52_high": setup.week52_high,
                "week52_low": setup.week52_low,
                "pct_from_52w_high": setup.pct_from_52w_high,
                "pct_above_52w_low": setup.pct_above_52w_low,
                # Moving Averages
                "sma_20_trend": setup.sma_20_trend,
                "sma_50_trend": setup.sma_50_trend,
                "sma_200_trend": setup.sma_200_trend,
                "ema_9_trend": setup.ema_9_trend,
                "ema_26_trend": setup.ema_26_trend,
                "ma_summary": setup.ma_summary,
                # Binance multi-timeframe volume
                "binance_vol_4h": setup.binance_vol_4h,
                "binance_vol_1d": setup.binance_vol_1d,
                "binance_vol_3d": setup.binance_vol_3d,
                "binance_vol_7d": setup.binance_vol_7d,
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
                # Volume & Performance
                "volume": setup.volume,
                "volume_usd": setup.volume_usd,
                "vwma": setup.vwma,
                "price_high": setup.price_high,
                "price_low": setup.price_low,
                "change_1d": setup.change_1d,
                "change_1w": setup.change_1w,
                "change_1m": setup.change_1m,
                "change_3m": setup.change_3m,
                "change_6m": setup.change_6m,
                "change_1y": setup.change_1y,
                "change_ytd": setup.change_ytd,
                # Leading Indicators
                "unusual_volume": setup.unusual_volume,
                "rsi_14": setup.rsi_14,
                "rsi_divergence": setup.rsi_divergence,
                "stoch_rsi": setup.stoch_rsi,
                "stoch_rsi_k": setup.stoch_rsi_k,
                "cci_20": setup.cci_20,
                "williams": setup.williams,
                "macd_signal": setup.macd_signal,
                "adx_signal": setup.adx_signal,
                "bb_upper": setup.bb_upper,
                "bb_lower": setup.bb_lower,
                "bb_cross_upper": setup.bb_cross_upper,
                "bb_cross_lower": setup.bb_cross_lower,
                # All-Time High
                "ath_price": setup.ath_price,
                "ath_date": setup.ath_date,
                "pct_from_ath": setup.pct_from_ath,
                "days_from_ath": setup.days_from_ath,
                # 52-Week Range
                "week52_high": setup.week52_high,
                "week52_low": setup.week52_low,
                "pct_from_52w_high": setup.pct_from_52w_high,
                "pct_above_52w_low": setup.pct_above_52w_low,
                # Moving Averages
                "sma_20_trend": setup.sma_20_trend,
                "sma_50_trend": setup.sma_50_trend,
                "sma_200_trend": setup.sma_200_trend,
                "ema_9_trend": setup.ema_9_trend,
                "ema_26_trend": setup.ema_26_trend,
                "ma_summary": setup.ma_summary,
                # Binance multi-timeframe volume
                "binance_vol_4h": setup.binance_vol_4h,
                "binance_vol_1d": setup.binance_vol_1d,
                "binance_vol_3d": setup.binance_vol_3d,
                "binance_vol_7d": setup.binance_vol_7d,
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
