# -*- coding: utf-8 -*-
"""
notifiers/discord_notifier.py

Discord webhook notifier — stub ready for implementation.
Uncomment and fill in the send() body when Discord support is needed.
"""

from src.models.trade_setup import TradeSetup
from src.notifiers.base import BaseNotifier


class DiscordNotifier(BaseNotifier):
    """
    Sends trade setup alerts to a Discord channel via webhook.

    Usage (in main.py):
        DiscordNotifier(webhook_url="https://discord.com/api/webhooks/...")
    """

    def __init__(self, webhook_url: str) -> None:
        self._webhook_url = webhook_url

    def send(self, setup: TradeSetup) -> None:
        # TODO: implement Discord webhook delivery
        # import requests
        # payload = {"content": f"**{setup.coin}** trade setup — {setup.date}"}
        # requests.post(self._webhook_url, json=payload, timeout=10)
        raise NotImplementedError("DiscordNotifier.send() is not yet implemented.")
