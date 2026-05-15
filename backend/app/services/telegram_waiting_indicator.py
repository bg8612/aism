from __future__ import annotations

import asyncio
import contextlib
import logging

from app.core.config import settings
from app.services.telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class TelegramWaitingIndicator:
    def __init__(self, telegram_client: TelegramClient) -> None:
        self.telegram_client = telegram_client
        self._typing_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._chat_id: int | None = None

    async def start(self, *, chat_id: int, reply_to_message_id: int | None = None) -> None:
        # reply_to_message_id kept for backward-compatible signature
        del reply_to_message_id
        self._chat_id = chat_id
        self._stop_event.clear()
        self._typing_task = asyncio.create_task(self._typing_loop(), name="telegram-typing-indicator")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._typing_task is not None:
            self._typing_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._typing_task
            self._typing_task = None
        self._chat_id = None

    async def _typing_loop(self) -> None:
        try:
            await asyncio.sleep(settings.telegram_waiting_indicator_delay_sec)
            while not self._stop_event.is_set():
                if self._chat_id is None:
                    return
                try:
                    await self.telegram_client.send_chat_action(chat_id=self._chat_id, action="typing")
                except Exception:
                    logger.exception("Failed to send Telegram typing action")
                    return
                # Telegram typing action lives for ~5 seconds.
                await asyncio.sleep(4.0)
        except asyncio.CancelledError:
            raise
