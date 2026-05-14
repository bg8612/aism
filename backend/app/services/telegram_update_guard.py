from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any

from app.core.config import settings


class TelegramUpdateGuard:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._seen_keys: set[str] = set()
        self._seen_queue: deque[tuple[float, str]] = deque()

    async def is_duplicate(self, update: dict[str, Any]) -> bool:
        key = self._build_key(update)
        if key is None:
            return False

        async with self._lock:
            self._prune_expired()
            if key in self._seen_keys:
                return True

            now = time.monotonic()
            self._seen_keys.add(key)
            self._seen_queue.append((now, key))
            return False

    def _build_key(self, update: dict[str, Any]) -> str | None:
        update_id = update.get("update_id")
        if isinstance(update_id, int):
            return f"update:{update_id}"

        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        message_id = message.get("message_id")
        if isinstance(chat_id, int) and isinstance(message_id, int):
            return f"message:{chat_id}:{message_id}"

        return None

    def _prune_expired(self) -> None:
        now = time.monotonic()
        ttl = settings.telegram_update_dedupe_ttl_sec
        while self._seen_queue and now - self._seen_queue[0][0] > ttl:
            _, key = self._seen_queue.popleft()
            self._seen_keys.discard(key)
