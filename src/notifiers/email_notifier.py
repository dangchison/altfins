# -*- coding: utf-8 -*-
"""
notifiers/email_notifier.py

Email notifier — stub ready for implementation.
Uncomment and fill in the send() body when email support is needed.
"""

from src.models.trade_setup import TradeSetup
from src.notifiers.base import BaseNotifier


class EmailNotifier(BaseNotifier):
    """
    Sends trade setup alerts via email (SMTP).

    Usage (in main.py):
        EmailNotifier(
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            username="your@email.com",
            password="app-password",
            recipients=["subscriber@email.com"],
        )
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        recipients: list[str],
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._recipients = recipients

    def send(self, setup: TradeSetup) -> None:
        # TODO: implement SMTP delivery
        # import smtplib
        # from email.mime.text import MIMEText
        # ...
        raise NotImplementedError("EmailNotifier.send() is not yet implemented.")
