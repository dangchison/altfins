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
    
    -- New fields for rich market data
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

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_crypto_setup UNIQUE (symbol, source_type, category, pattern_name, date)
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_crypto_analysis_symbol ON crypto_analysis(symbol);
CREATE INDEX IF NOT EXISTS idx_crypto_analysis_date ON crypto_analysis(date);
