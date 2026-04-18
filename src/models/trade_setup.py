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

    # Parsed fields — populated by the parser layer
    setup: str = "N/A"
    pattern: str = "N/A"
    s_trend: str = "N/A"
    m_trend: str = "N/A"
    l_trend: str = "N/A"
    momentum: str = "N/A"
    rsi: str = "N/A"
    support: str = "N/A"
    resistance: str = "N/A"
