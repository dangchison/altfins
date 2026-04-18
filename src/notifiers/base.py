# -*- coding: utf-8 -*-
"""
notifiers/base.py

Strategy interface for all notification channels.
Adding a new channel = write a new class that implements BaseNotifier.
The pipeline doesn't need to change.
"""

from abc import ABC, abstractmethod

from src.models.trade_setup import TradeSetup


class BaseNotifier(ABC):

    @abstractmethod
    def send(self, setup: TradeSetup) -> None:
        """
        Deliver a notification for the given trade setup.
        Implementations must handle their own errors internally and
        must NOT raise — the pipeline fans out to all notifiers and
        a single failure must not block the rest.
        """
