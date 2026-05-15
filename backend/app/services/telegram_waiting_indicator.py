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
        self._animation_task: asyncio.Task | None = None
        self._starter_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._chat_id: int | None = None
        self._message_id: int | None = None
        self._reply_to_message_id: int | None = None

    async def start(self, *, chat_id: int, reply_to_message_id: int | None = None) -> None:
        self._chat_id = chat_id
        self._reply_to_message_id = reply_to_message_id
        self._stop_event.clear()
        self._starter_task = asyncio.create_task(self._delayed_start(), name="telegram-waiting-starter")

    async def stop(self) -> None:
        self._stop_event.set()

        if self._starter_task is not None:
            self._starter_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._starter_task
            self._starter_task = None

        if self._animation_task is not None:
            self._animation_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._animation_task
            self._animation_task = None

        if self._chat_id is None or self._message_id is None:
            return

        try:
            await self.telegram_client.delete_message(self._chat_id, self._message_id)
        except Exception:
            logger.exception("Failed to delete Telegram waiting indicator")
        finally:
            self._chat_id = None
            self._message_id = None
            self._reply_to_message_id = None

    async def _delayed_start(self) -> None:
        try:
            await asyncio.sleep(settings.telegram_waiting_indicator_delay_sec)
            if self._stop_event.is_set() or self._chat_id is None:
                return

            response = await self.telegram_client.send_message(
                chat_id=self._chat_id,
                text="Думаю над ответом.",
                reply_to_message_id=self._reply_to_message_id,
            )
            result = response.get("result") or {}
            message_id = result.get("message_id")
            if isinstance(message_id, int):
                self._message_id = message_id
                self._animation_task = asyncio.create_task(self._animate(), name="telegram-waiting-indicator")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to start Telegram waiting indicator")

    async def _animate(self) -> None:
        if self._chat_id is None or self._message_id is None:
            return

        frames = [
            "Думаю над ответом.",
            "Думаю над ответом..",
            "Думаю над ответом...",
        ]
        frame_index = 0

        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(settings.telegram_waiting_indicator_frame_sec)
                frame_index = (frame_index + 1) % len(frames)
                await self.telegram_client.edit_message_text(
                    self._chat_id,
                    self._message_id,
                    frames[frame_index],
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Failed to animate Telegram waiting indicator")
                return
