# -*- coding: utf-8 -*-
"""
main.py

Application entry point.
Wires up dependencies and runs the pipeline.
Add new notifiers here — no other file needs to change.
"""

from src.config import settings
from src.notifiers.telegram_notifier import TelegramNotifier
from src.pipeline import ScrapePipeline
from src.repositories.supabase_repository import SupabaseRepository


def main() -> None:
    repo = SupabaseRepository(
        url=settings.supabase_url,
        key=settings.supabase_key,
    )

    notifiers = [
        TelegramNotifier(
            token=settings.telegram_bot_token,
            chat_ids=settings.chat_id_list,
        ),
        # DiscordNotifier(webhook_url="..."),  # uncomment when ready
        # EmailNotifier(...),                  # uncomment when ready
    ]

    pipeline = ScrapePipeline(repo=repo, notifiers=notifiers)
    pipeline.run()


if __name__ == "__main__":
    main()
