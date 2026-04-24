-- Migration: Add indicator columns to crypto_analysis
-- Run this in Supabase SQL Editor

ALTER TABLE crypto_analysis
  -- Volume & Performance (Indicators drawer — Grid 4)
  ADD COLUMN IF NOT EXISTS volume TEXT,
  ADD COLUMN IF NOT EXISTS volume_usd TEXT,
  ADD COLUMN IF NOT EXISTS vwma TEXT,
  ADD COLUMN IF NOT EXISTS price_high TEXT,
  ADD COLUMN IF NOT EXISTS price_low TEXT,
  ADD COLUMN IF NOT EXISTS change_1d TEXT,
  ADD COLUMN IF NOT EXISTS change_1w TEXT,
  ADD COLUMN IF NOT EXISTS change_1m TEXT,
  ADD COLUMN IF NOT EXISTS change_3m TEXT,
  ADD COLUMN IF NOT EXISTS change_6m TEXT,
  ADD COLUMN IF NOT EXISTS change_1y TEXT,
  ADD COLUMN IF NOT EXISTS change_ytd TEXT,

  -- Leading Indicators (Indicators drawer — Grid 0)
  ADD COLUMN IF NOT EXISTS unusual_volume TEXT,
  ADD COLUMN IF NOT EXISTS rsi_14 TEXT,
  ADD COLUMN IF NOT EXISTS rsi_divergence TEXT,
  ADD COLUMN IF NOT EXISTS stoch_rsi TEXT,
  ADD COLUMN IF NOT EXISTS stoch_rsi_k TEXT,
  ADD COLUMN IF NOT EXISTS cci_20 TEXT,
  ADD COLUMN IF NOT EXISTS williams TEXT,
  ADD COLUMN IF NOT EXISTS macd_signal TEXT,
  ADD COLUMN IF NOT EXISTS adx_signal TEXT,
  ADD COLUMN IF NOT EXISTS bb_upper TEXT,
  ADD COLUMN IF NOT EXISTS bb_lower TEXT,
  ADD COLUMN IF NOT EXISTS bb_cross_upper TEXT,
  ADD COLUMN IF NOT EXISTS bb_cross_lower TEXT,

  -- All-Time High (Indicators drawer — Grid 1)
  ADD COLUMN IF NOT EXISTS ath_price TEXT,
  ADD COLUMN IF NOT EXISTS ath_date TEXT,
  ADD COLUMN IF NOT EXISTS pct_from_ath TEXT,
  ADD COLUMN IF NOT EXISTS days_from_ath TEXT,

  -- 52-Week Range (Indicators drawer — Grid 2)
  ADD COLUMN IF NOT EXISTS week52_high TEXT,
  ADD COLUMN IF NOT EXISTS week52_low TEXT,
  ADD COLUMN IF NOT EXISTS pct_from_52w_high TEXT,
  ADD COLUMN IF NOT EXISTS pct_above_52w_low TEXT,

  -- Key Moving Averages (Indicators drawer — Grid 3)
  ADD COLUMN IF NOT EXISTS sma_20_trend TEXT,
  ADD COLUMN IF NOT EXISTS sma_50_trend TEXT,
  ADD COLUMN IF NOT EXISTS sma_200_trend TEXT,
  ADD COLUMN IF NOT EXISTS ema_9_trend TEXT,
  ADD COLUMN IF NOT EXISTS ema_26_trend TEXT,
  ADD COLUMN IF NOT EXISTS ma_summary TEXT,

  -- Trend Scorecard (altfins-scorecard shadow DOM)
  ADD COLUMN IF NOT EXISTS s_trend TEXT,
  ADD COLUMN IF NOT EXISTS m_trend TEXT,
  ADD COLUMN IF NOT EXISTS l_trend TEXT,

  -- Binance multi-timeframe volume (public API, no auth required)
  ADD COLUMN IF NOT EXISTS binance_vol_4h TEXT,
  ADD COLUMN IF NOT EXISTS binance_vol_1d TEXT,
  ADD COLUMN IF NOT EXISTS binance_vol_3d TEXT,
  ADD COLUMN IF NOT EXISTS binance_vol_7d TEXT;
