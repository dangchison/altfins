# -*- coding: utf-8 -*-
"""
notifiers/telegram_notifier.py

Sends trade setup alerts to one or more Telegram chat IDs.
Multi-group support: pass a list of chat IDs; each receives all messages.
"""
from __future__ import annotations

from typing import Optional

import requests

from src.models.trade_setup import TradeSetup
from src.notifiers.base import BaseNotifier
from src.parsers.altfins_parser import format_telegram_message
from src.logger import get_logger
from src.utils.retry import with_retry

log = get_logger(__name__)

_API_BASE = "https://api.telegram.org/bot{token}/{method}"


class TelegramNotifier(BaseNotifier):

    def __init__(self, token: str, chat_ids: list[str]) -> None:
        """
        Args:
            token:    Telegram bot token.
            chat_ids: One or more chat/group IDs to deliver alerts to.
        """
        self._token = token
        self._chat_ids = chat_ids

    # ------------------------------------------------------------------
    # BaseNotifier implementation
    # ------------------------------------------------------------------

    def send(self, setup: TradeSetup) -> None:
        """Fan-out all messages to every configured chat ID."""
        for chat_id in self._chat_ids:
            # 1. Try sending Photo if available
            if setup.image_url and setup.image_url.startswith("http"):
                try:
                    log.debug("Sending photo: %s", setup.image_url)
                    self._send_photo(
                        chat_id=chat_id,
                        photo_url=setup.image_url,
                        caption=f"📊 <a href=\"https://www.binance.com/trade/{setup.symbol}_USDT\">{setup.symbol}</a> | {setup.date}",
                    )
                except Exception as e:
                    log.warning("Failed to send photo (falling back to text only): %s", e)
            
            # 2. Try sending the formatted HTML message
            try:
                self._send_message(
                    chat_id=chat_id,
                    text=format_telegram_message(setup),
                    parse_mode="HTML",
                )
                log.info("📢 Alert sent successfully")
            except Exception as exc:
                log.error("Failed to send text alert: %s", exc)

    # ------------------------------------------------------------------
    # Private HTTP helpers
    # ------------------------------------------------------------------

    @with_retry(max_attempts=3, base_delay=2.0)
    def _send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: Optional[str] = "HTML",
    ) -> None:
        url = _API_BASE.format(token=self._token, method="sendMessage")
        payload: dict = {"chat_id": chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        response = requests.post(url, data=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram sendMessage error (chat {chat_id}): {result}")

    @with_retry(max_attempts=3, base_delay=2.0)
    def _send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: str = "",
        parse_mode: Optional[str] = "HTML",
    ) -> None:
        """
        Download the photo and send it as a file. This is more robust than 
        sending by URL, especially when the source has no extension or wrong content-type.
        """
        url = _API_BASE.format(token=self._token, method="sendPhoto")
        
        try:
            # 1. Download the photo to memory
            photo_res = requests.get(photo_url, timeout=10)
            photo_res.raise_for_status()
            photo_data = photo_res.content
            
            # 2. Send as multipart/form-data
            files = {"photo": ("chart.png", photo_data, "image/png")}
            payload: dict = {"chat_id": chat_id, "caption": caption}
            if parse_mode:
                payload["parse_mode"] = parse_mode

            response = requests.post(url, data=payload, files=files, timeout=15)
            response.raise_for_status()
            
        except Exception as e:
            # Fallback: Try sending by URL if download fails (less likely to work but worth a try)
            log.debug("Photo download/upload failed, trying direct URL: %s", e)
            payload: dict = {"chat_id": chat_id, "photo": photo_url, "caption": caption}
            if parse_mode:
                payload["parse_mode"] = parse_mode
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()

        result = response.json()
        if not result.get("ok"):
            raise RuntimeError(f"Telegram sendPhoto error: {result}")
