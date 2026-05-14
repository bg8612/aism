from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.services.dialogue_storage_service import DialogueStorageService
from app.services.openrouter_client import OpenRouterClient
from app.services.telegram_client import TelegramClient
from app.services.telegram_update_guard import TelegramUpdateGuard
from app.services.telegram_waiting_indicator import TelegramWaitingIndicator

router = APIRouter(prefix="/telegram", tags=["telegram"])

openrouter_client = OpenRouterClient()
telegram_client = TelegramClient()
dialogue_storage_service = DialogueStorageService()
telegram_update_guard = TelegramUpdateGuard()


def _extract_text_payload(update: dict[str, Any]) -> tuple[int | None, int | None, str | None]:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}

    chat_id = chat.get("id")
    message_id = message.get("message_id")
    text = message.get("text") or message.get("caption")

    if isinstance(chat_id, int) and isinstance(text, str):
        return chat_id, message_id if isinstance(message_id, int) else None, text.strip()

    return None, None, None


@router.post("/webhook")
async def telegram_webhook(
    update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, Any]:
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid telegram secret token")

    if await telegram_update_guard.is_duplicate(update):
        return {"ok": True, "skipped": "duplicate_update"}

    chat_id, message_id, user_text = _extract_text_payload(update)
    if chat_id is None or not user_text:
        return {"ok": True, "skipped": "no_text_message"}

    dialogue_context = await dialogue_storage_service.save_user_message_from_telegram(update=update, user_text=user_text)
    model_context = await dialogue_storage_service.get_model_context(
        context=dialogue_context,
        user_text=user_text,
    )
    waiting_indicator = TelegramWaitingIndicator(telegram_client)
    await waiting_indicator.start(chat_id=chat_id, reply_to_message_id=message_id)

    try:
        reply = await openrouter_client.generate_reply(
            user_text,
            conversation_messages=model_context.conversation_messages,
            memory_notes=model_context.memory_notes,
        )
    except Exception:
        reply = "Сервис временно недоступен. Попробуйте еще раз через минуту."
    finally:
        await waiting_indicator.stop()

    await dialogue_storage_service.save_bot_reply(
        context=dialogue_context,
        reply_text=reply,
        raw_payload_json={"source": "telegram_webhook"},
    )

    try:
        await telegram_client.send_message(chat_id=chat_id, text=reply, reply_to_message_id=message_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Telegram send failed: {exc}") from exc

    return {"ok": True}


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
