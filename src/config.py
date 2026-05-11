# -*- coding: utf-8 -*-
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized configuration loaded from environment variables.
    Single source of truth — no os.getenv() scattered across files.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    altfins_account: str
    altfins_password: str

    supabase_url: str
    supabase_key: str

    telegram_bot_token: str

    telegram_chat_id_analysis: str = ""
    telegram_chat_id_pattern: str = ""
    telegram_chat_id_highlight: str = ""

    # Scraper behaviour
    technical_analysis_max_rows: int = 2
    enable_technical_analysis: bool = True
    enable_chart_patterns: bool = True
    enable_market_highlights: bool = True
    use_persistent_session: bool = True




_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        try:
            _settings = Settings()
        except Exception as exc:
            raise RuntimeError(
                f"Configuration error — check .env file.\n"
                f"Required: ALTFINS_ACCOUNT, ALTFINS_PASSWORD, "
                f"SUPABASE_URL, SUPABASE_KEY, TELEGRAM_BOT_TOKEN\n"
                f"Detail: {exc}"
            ) from exc
    return _settings
