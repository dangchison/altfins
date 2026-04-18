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
            self._send_photo(
                chat_id=chat_id,
                photo_url=setup.image_url,
                caption=f"📊 Chart for {setup.coin} ({setup.symbol}) - {setup.date}",
            )
            self._send_message(
                chat_id=chat_id,
                text=f"🔬 {setup.symbol} - {setup.date} - {setup.raw_text}",
                parse_mode=None,
            )
            self._send_message(
                chat_id=chat_id,
                text=format_telegram_message(setup),
                parse_mode="HTML",
            )

    # ------------------------------------------------------------------
    # Private HTTP helpers
    # ------------------------------------------------------------------

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

        try:
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            if not result.get("ok"):
                print(f"⚠️ Telegram sendMessage error (chat {chat_id}): {result}")
        except Exception as exc:
            print(f"❌ Telegram sendMessage exception (chat {chat_id}): {exc}")

    def _send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: str = "",
        parse_mode: Optional[str] = "HTML",
    ) -> None:
        url = _API_BASE.format(token=self._token, method="sendPhoto")
        payload: dict = {"chat_id": chat_id, "photo": photo_url, "caption": caption}
        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            response = requests.post(url, data=payload, timeout=10)
            result = response.json()
            if not result.get("ok"):
                print(f"⚠️ Telegram sendPhoto error (chat {chat_id}): {result}")
        except Exception as exc:
            print(f"❌ Telegram sendPhoto exception (chat {chat_id}): {exc}")
