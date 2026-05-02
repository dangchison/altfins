-- Migration: Add breakout signal fields to crypto_analysis
-- Run this against your Supabase DB

ALTER TABLE crypto_analysis
  ADD COLUMN IF NOT EXISTS breakout_signal BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS breakout_confidence INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS breakout_entry TEXT,
  ADD COLUMN IF NOT EXISTS breakout_stop TEXT,
  ADD COLUMN IF NOT EXISTS breakout_target TEXT,
  ADD COLUMN IF NOT EXISTS breakout_rr TEXT,
  ADD COLUMN IF NOT EXISTS breakout_reasons TEXT,
  ADD COLUMN IF NOT EXISTS breakout_timeframe TEXT;
