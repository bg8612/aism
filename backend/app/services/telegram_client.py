from __future__ import annotations

import httpx

from app.core.config import settings


class TelegramClient:
    @property
    def _base_url(self) -> str:
        if not settings.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")
        return f"https://api.telegram.org/bot{settings.telegram_bot_token}"

    async def send_message(self, chat_id: int, text: str, reply_to_message_id: int | None = None) -> None:
        payload: dict[str, object] = {
            "chat_id": chat_id,
            "text": text[: settings.bot_reply_max_chars],
        }
        if reply_to_message_id is not None:
            payload["reply_to_message_id"] = reply_to_message_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/sendMessage", json=payload)
            response.raise_for_status()

    async def set_webhook(self, webhook_url: str, secret_token: str = "") -> dict:
        payload: dict[str, object] = {"url": webhook_url}
        if secret_token:
            payload["secret_token"] = secret_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self._base_url}/setWebhook", json=payload)
            response.raise_for_status()
            return response.json()
