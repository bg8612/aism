from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.config import settings
from app.services.openrouter_client import OpenRouterClient
from app.services.telegram_client import TelegramClient

logger = logging.getLogger(__name__)


class TelegramPollingRunner:
    def __init__(self, telegram_client: TelegramClient, openrouter_client: OpenRouterClient) -> None:
        self.telegram_client = telegram_client
        self.openrouter_client = openrouter_client
        self._task: asyncio.Task | None = None
        self._offset: int | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        await self.telegram_client.delete_webhook(drop_pending_updates=False)
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="telegram-polling-runner")
        logger.info("Telegram polling runner started")

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Telegram polling runner stopped")

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                updates = await self.telegram_client.get_updates(
                    offset=self._offset,
                    timeout_sec=settings.telegram_poll_timeout_sec,
                    limit=settings.telegram_poll_limit,
                )
                for update in updates:
                    update_id = update.get("update_id")
                    if isinstance(update_id, int):
                        self._offset = update_id + 1
                    await self._handle_update(update)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Polling loop error: %s", exc)
                await asyncio.sleep(2)

    async def _handle_update(self, update: dict[str, Any]) -> None:
        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        message_id = message.get("message_id")
        text = message.get("text") or message.get("caption")

        if not isinstance(chat_id, int) or not isinstance(text, str) or not text.strip():
            return

        user_text = text.strip()

        try:
            reply = await self.openrouter_client.generate_reply(user_text)
        except Exception:
            reply = "I could not get a model response right now. Please try again in a minute."

        await self.telegram_client.send_message(
            chat_id=chat_id,
            text=reply,
            reply_to_message_id=message_id if isinstance(message_id, int) else None,
        )
