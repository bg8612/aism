from __future__ import annotations

import httpx

from app.core.config import settings


class TelegramClient:
    def __init__(self, bot_token: str | None = None) -> None:
        self._bot_token = bot_token

    @property
    def _base_url(self) -> str:
        token = self._bot_token or settings.telegram_bot_token
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        return f"https://api.telegram.org/bot{token}"

    async def send_message(
        self,
        chat_id: int,
        text: str,
        reply_to_message_id: int | None = None,
    ) -> dict:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "text": text[: settings.bot_reply_max_chars],
        }
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/sendMessage", json=payload)
            response.raise_for_status()
            return response.json()

    async def edit_message_text(self, chat_id: int, message_id: int, text: str) -> dict:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text[: settings.bot_reply_max_chars],
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/editMessageText", json=payload)
            response.raise_for_status()
            return response.json()

    async def delete_message(self, chat_id: int, message_id: int) -> dict:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/deleteMessage", json=payload)
            response.raise_for_status()
            return response.json()

    async def set_webhook(self, webhook_url: str, secret_token: str = "") -> dict:
        payload: dict[str, object] = {"url": webhook_url}
        if secret_token:
            payload["secret_token"] = secret_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/setWebhook", json=payload)
            response.raise_for_status()
            return response.json()

    async def delete_webhook(self, drop_pending_updates: bool = False) -> dict:
        payload = {"drop_pending_updates": drop_pending_updates}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/deleteWebhook", json=payload)
            response.raise_for_status()
            return response.json()

    async def get_webhook_info(self) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{self._base_url}/getWebhookInfo")
            response.raise_for_status()
            return response.json()

    async def get_updates(self, offset: int | None = None, timeout_sec: int = 30, limit: int = 20) -> list[dict]:
        payload: dict[str, int] = {"timeout": timeout_sec, "limit": limit}
        if offset is not None:
            payload["offset"] = offset

        async with httpx.AsyncClient(timeout=timeout_sec + 15.0) as client:
            response = await client.post(f"{self._base_url}/getUpdates", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("result") or []

    async def send_chat_action(self, chat_id: int, action: str = "typing") -> dict:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "action": action,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/sendChatAction", json=payload)
            response.raise_for_status()
            return response.json()
