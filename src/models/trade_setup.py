# -*- coding: utf-8 -*-
from pydantic import BaseModel


class TradeSetup(BaseModel):
    """
    Unified data contract for a single trade setup entry.
    All layers (scraper, parser, repository, notifiers) use this model.
    """

    date: str
    coin: str
    symbol: str
    raw_text: str
    image_url: str

    # Metadata for multi-source support
    source_type: str = "TECHNICAL_ANALYSIS"
    category: str = "N/A"
    pattern_name: str = "N/A"
    price: str = "N/A"
    price_change: str = "N/A"

    # Parsed fields — populated by the parser layer
    setup: str = "N/A"
    pattern: str = "N/A"
    interval: str = "N/A"
    status: str = "N/A"
    signal: str = "N/A"
    s_trend: str = "N/A"
    m_trend: str = "N/A"
    l_trend: str = "N/A"
    momentum: str = "N/A"
    rsi: str = "N/A"
    support: str = "N/A"
    resistance: str = "N/A"
    profit_potential: str = "N/A"

    # Volume & Performance (Indicators drawer — Grid 4)
    volume: str = "N/A"
    volume_usd: str = "N/A"
    vwma: str = "N/A"
    price_high: str = "N/A"
    price_low: str = "N/A"
    change_1d: str = "N/A"
    change_1w: str = "N/A"
    change_1m: str = "N/A"
    change_3m: str = "N/A"
    change_6m: str = "N/A"
    change_1y: str = "N/A"
    change_ytd: str = "N/A"

    # Leading Indicators (Indicators drawer — Grid 0)
    unusual_volume: str = "N/A"
    rsi_14: str = "N/A"
    rsi_divergence: str = "N/A"
    stoch_rsi: str = "N/A"
    stoch_rsi_k: str = "N/A"
    cci_20: str = "N/A"
    williams: str = "N/A"
    macd_signal: str = "N/A"
    adx_signal: str = "N/A"
    bb_upper: str = "N/A"
    bb_lower: str = "N/A"
    bb_cross_upper: str = "N/A"
    bb_cross_lower: str = "N/A"

    # All-Time High (Indicators drawer — Grid 1)
    ath_price: str = "N/A"
    ath_date: str = "N/A"
    pct_from_ath: str = "N/A"
    days_from_ath: str = "N/A"

    # 52-Week Range (Indicators drawer — Grid 2)
    week52_high: str = "N/A"
    week52_low: str = "N/A"
    pct_from_52w_high: str = "N/A"
    pct_above_52w_low: str = "N/A"

    # Key Moving Averages (Indicators drawer — Grid 3)
    sma_20_trend: str = "N/A"
    sma_50_trend: str = "N/A"
    sma_200_trend: str = "N/A"
    ema_9_trend: str = "N/A"
    ema_26_trend: str = "N/A"
    ma_summary: str = "N/A"    # Full MA grid as JSON string

