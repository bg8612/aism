from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.services.openrouter_client import OpenRouterClient
from app.services.telegram_client import TelegramClient
from app.services.telegram_message_handler import TelegramMessageHandler
from app.services.telegram_update_guard import TelegramUpdateGuard

router = APIRouter(prefix="/telegram", tags=["telegram"])

openrouter_client = OpenRouterClient()
telegram_client = TelegramClient()
telegram_message_handler = TelegramMessageHandler(telegram_client, openrouter_client)
telegram_update_guard = TelegramUpdateGuard()


@router.post("/webhook")
async def telegram_webhook(
    update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, Any]:
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid telegram secret token")

    if await telegram_update_guard.is_duplicate(update):
        return {"ok": True, "skipped": "duplicate_update"}
    try:
        return await telegram_message_handler.handle_telegram_message(update=update, source="telegram_webhook")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Telegram handling failed: {exc}") from exc


@router.post("/set-webhook")
async def set_telegram_webhook(x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    if settings.admin_api_token:
        if x_admin_token != settings.admin_api_token:
            raise HTTPException(status_code=401, detail="Invalid admin token")

    if not settings.telegram_webhook_url:
        raise HTTPException(status_code=400, detail="TELEGRAM_WEBHOOK_URL is not configured")

    try:
        result = await telegram_client.set_webhook(
            webhook_url=settings.telegram_webhook_url,
            secret_token=settings.telegram_webhook_secret,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"setWebhook failed: {exc}") from exc

    return {"ok": True, "result": result}


@router.get("/webhook-info")
async def get_telegram_webhook_info(x_admin_token: str | None = Header(default=None)) -> dict[str, Any]:
    if settings.admin_api_token:
        if x_admin_token != settings.admin_api_token:
            raise HTTPException(status_code=401, detail="Invalid admin token")

    try:
        result = await telegram_client.get_webhook_info()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"getWebhookInfo failed: {exc}") from exc

    return {"ok": True, "result": result}
