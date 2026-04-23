-- Database Schema for Altfins Scraper
-- Table: crypto_analysis

CREATE TABLE IF NOT EXISTS crypto_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    coin TEXT NOT NULL,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    contents TEXT,
    image TEXT,
    source_type TEXT DEFAULT 'TECHNICAL_ANALYSIS',
    category TEXT,
    pattern_name TEXT,

    -- Core pattern fields
    setup TEXT,
    pattern TEXT,
    interval TEXT,
    status TEXT,
    signal TEXT,
    s_trend TEXT,
    m_trend TEXT,
    l_trend TEXT,
    momentum TEXT,
    rsi TEXT,
    support TEXT,
    resistance TEXT,
    profit_potential TEXT,
    price TEXT,
    price_change TEXT,

    -- Volume & Performance (from Indicators drawer — Grid 4)
    volume TEXT,               -- Coin volume 24h (e.g. "5,507,988.00")
    volume_usd TEXT,           -- Volume in USD (e.g. "1,366,841")
    vwma TEXT,                 -- Volume-Weighted Moving Average
    price_high TEXT,           -- Day High
    price_low TEXT,            -- Day Low
    change_1d TEXT,            -- 1D % change
    change_1w TEXT,            -- 1W % change
    change_1m TEXT,            -- 1M % change
    change_3m TEXT,            -- 3M % change
    change_6m TEXT,            -- 6M % change
    change_1y TEXT,            -- 1Y % change
    change_ytd TEXT,           -- YTD % change

    -- Leading Indicators (from drawer — Grid 0)
    unusual_volume TEXT,       -- Unusual Volume Spike (Yes / -)
    rsi_14 TEXT,               -- RSI 14 trend (Neutral/Overbought/Oversold)
    rsi_divergence TEXT,       -- RSI Divergence signal
    stoch_rsi TEXT,            -- Stochastic RSI Fast (Overbought/Oversold)
    stoch_rsi_k TEXT,          -- Stochastic RSI (K) numeric value
    cci_20 TEXT,               -- CCI 20 trend
    williams TEXT,             -- Williams %R trend
    macd_signal TEXT,          -- MACD signal (Bullish/Bearish)
    adx_signal TEXT,           -- ADX signal (Neutral/Trending)
    bb_upper TEXT,             -- Upper Bollinger Band value
    bb_lower TEXT,             -- Lower Bollinger Band value
    bb_cross_upper TEXT,       -- Price crossed Upper BB (Yes/No)
    bb_cross_lower TEXT,       -- Price crossed Lower BB (Yes/No)

    -- All-Time High (from drawer — Grid 1)
    ath_price TEXT,            -- All Time High Price ($)
    ath_date TEXT,             -- ATH Date
    pct_from_ath TEXT,         -- % Down from ATH
    days_from_ath TEXT,        -- Days since ATH

    -- 52-Week Range (from drawer — Grid 2)
    week52_high TEXT,          -- 52-Week High
    week52_low TEXT,           -- 52-Week Low
    pct_from_52w_high TEXT,    -- % Down from 52-Week High
    pct_above_52w_low TEXT,    -- % Above 52-Week Low

    -- Key Moving Averages (from drawer — Grid 3)
    sma_20_trend TEXT,         -- SMA 20 Trend (Up/Down)
    sma_50_trend TEXT,         -- SMA 50 Trend (Up/Down)
    sma_200_trend TEXT,        -- SMA 200 Trend (Up/Down)
    ema_9_trend TEXT,          -- EMA 9 Trend (Up/Down)
    ema_26_trend TEXT,         -- EMA 26 Trend (Up/Down)
    ma_summary TEXT,           -- Full MA grid as JSON for completeness

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_crypto_setup UNIQUE (symbol, source_type, category, pattern_name, date)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_crypto_analysis_symbol ON crypto_analysis(symbol);
CREATE INDEX IF NOT EXISTS idx_crypto_analysis_date ON crypto_analysis(date);
