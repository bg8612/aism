from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.conversation import Conversation
from app.repositories.bot_repository import BotRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.end_user_repository import EndUserRepository
from app.repositories.message_repository import MessageRepository

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DialogueContext:
    bot_id: int
    end_user_id: int
    conversation_id: int
    latest_user_message_id: int | None = None
    channel: str = "telegram"


@dataclass(slots=True)
class ModelContext:
    conversation_messages: list[dict[str, str]]
    memory_notes: list[str]


class DialogueStorageService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
        bot_repository: BotRepository | None = None,
        end_user_repository: EndUserRepository | None = None,
        conversation_repository: ConversationRepository | None = None,
        message_repository: MessageRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._bot_repository = bot_repository or BotRepository()
        self._end_user_repository = end_user_repository or EndUserRepository()
        self._conversation_repository = conversation_repository or ConversationRepository()
        self._message_repository = message_repository or MessageRepository()

    async def get_model_context(
        self,
        *,
        context: DialogueContext | None,
        user_text: str,
    ) -> ModelContext:
        if context is None:
            return ModelContext(conversation_messages=[], memory_notes=[])

        include_memory_notes = self._should_include_memory_notes(user_text)
        load_limit = (
            settings.openrouter_memory_scan_message_limit
            if include_memory_notes
            else settings.openrouter_context_message_limit
        )

        async with self._session_factory() as session:
            try:
                stored_messages = await self._message_repository.list_recent_for_context(
                    session,
                    conversation_id=context.conversation_id,
                    limit=load_limit,
                )
            except SQLAlchemyError:
                logger.exception("Database error while loading conversation history")
                return ModelContext(conversation_messages=[], memory_notes=[])
            except Exception:
                logger.exception("Unexpected error while loading conversation history")
                return ModelContext(conversation_messages=[], memory_notes=[])

        role_map = {
            "user": "user",
            "bot": "assistant",
            "system": "system",
        }
        recent_messages = stored_messages[-settings.openrouter_context_message_limit :]
        model_messages: list[dict[str, str]] = []
        for stored_message in recent_messages:
            role = role_map.get(stored_message.sender_type)
            content = stored_message.message_text.strip()
            if role is None or not content:
                continue
            model_messages.append({"role": role, "content": content})

        memory_notes = self._extract_memory_notes(stored_messages) if include_memory_notes else []
        return ModelContext(
            conversation_messages=model_messages,
            memory_notes=memory_notes,
        )

    async def save_user_message_from_telegram(
        self,
        *,
        update: dict[str, Any],
        user_text: str,
    ) -> DialogueContext | None:
        message = update.get("message") or update.get("edited_message") or {}
        from_user = message.get("from") or {}
        chat = message.get("chat") or {}

        external_user_id = from_user.get("id") or chat.get("id")
        if external_user_id is None:
            return None

        async with self._session_factory() as session:
            try:
                bot = await self._bot_repository.get_or_create_telegram_bot(
                    session,
                    name=settings.bot_name,
                    telegram_bot_username=settings.telegram_bot_username or None,
                )
                end_user = await self._end_user_repository.get_or_create(
                    session,
                    bot_id=bot.id,
                    channel="telegram",
                    external_user_id=str(external_user_id),
                    username=from_user.get("username"),
                    first_name=from_user.get("first_name"),
                    last_name=from_user.get("last_name"),
                )
                conversation = await self._conversation_repository.get_or_create_active(
                    session,
                    bot_id=bot.id,
                    end_user_id=end_user.id,
                    channel="telegram",
                )
                created_message = await self._message_repository.create(
                    session,
                    conversation_id=conversation.id,
                    bot_id=bot.id,
                    end_user_id=end_user.id,
                    sender_type="user",
                    message_text=user_text,
                    raw_payload_json=update,
                )
                conversation.last_message_at = datetime.now(timezone.utc)
                await session.commit()

                return DialogueContext(
                    bot_id=bot.id,
                    end_user_id=end_user.id,
                    conversation_id=conversation.id,
                    latest_user_message_id=created_message.id,
                    channel="telegram",
                )
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Database error while saving incoming Telegram message")
            except Exception:
                await session.rollback()
                logger.exception("Unexpected error while saving incoming Telegram message")

        return None

    async def save_bot_reply(
        self,
        *,
        context: DialogueContext | None,
        reply_text: str,
        raw_payload_json: dict[str, Any] | None = None,
    ) -> None:
        if context is None:
            return

        async with self._session_factory() as session:
            try:
                await self._message_repository.create(
                    session,
                    conversation_id=context.conversation_id,
                    bot_id=context.bot_id,
                    end_user_id=context.end_user_id,
                    sender_type="bot",
                    message_text=reply_text,
                    raw_payload_json=raw_payload_json,
                )
                conversation = await session.get(Conversation, context.conversation_id)
                if conversation is not None:
                    conversation.last_message_at = datetime.now(timezone.utc)
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Database error while saving bot reply")
            except Exception:
                await session.rollback()
                logger.exception("Unexpected error while saving bot reply")

    async def has_newer_user_message(
        self,
        *,
        context: DialogueContext | None,
    ) -> bool:
        if context is None or context.latest_user_message_id is None:
            return False

        async with self._session_factory() as session:
            try:
                return await self._message_repository.has_newer_user_message(
                    session,
                    conversation_id=context.conversation_id,
                    after_message_id=context.latest_user_message_id,
                )
            except SQLAlchemyError:
                logger.exception("Database error while checking newer user messages")
            except Exception:
                logger.exception("Unexpected error while checking newer user messages")
        return False

    def _extract_memory_notes(self, stored_messages: list[Any]) -> list[str]:
        notes: list[str] = []
        seen: set[str] = set()

        for stored_message in reversed(stored_messages):
            if stored_message.sender_type != "user":
                continue

            note = self._extract_memory_note_from_text(stored_message.message_text)
            if note is None:
                continue

            normalized_note = note.casefold()
            if normalized_note in seen:
                continue

            seen.add(normalized_note)
            notes.append(note)
            if len(notes) >= settings.openrouter_memory_note_limit:
                break

        notes.reverse()
        return notes

    def _extract_memory_note_from_text(self, text: str) -> str | None:
        normalized = " ".join(text.strip().split())
        lowered = normalized.casefold()
        triggers = [
            "запомни ",
            "запомни, ",
            "пожалуйста запомни ",
            "прошу запомнить ",
            "нужно запомнить ",
            "сделай заметку ",
            "сделай заметку: ",
            "добавь в заметки ",
            "запиши ",
            "запиши: ",
        ]

        for trigger in triggers:
            index = lowered.find(trigger)
            if index == -1:
                continue

            note = normalized[index + len(trigger) :].strip(" .,!?:;\"'")
            if len(note) < 2:
                return None
            note = self._strip_wrapping_quotes(note)
            if len(note) < 2:
                return None
            return note[:300]

        return None

    def _strip_wrapping_quotes(self, text: str) -> str:
        quote_pairs = [
            ('"', '"'),
            ("'", "'"),
            ("«", "»"),
            ("“", "”"),
        ]
        stripped = text.strip()
        for left_quote, right_quote in quote_pairs:
            if stripped.startswith(left_quote) and stripped.endswith(right_quote) and len(stripped) >= 2:
                return stripped[1:-1].strip()
        return stripped

    def _should_include_memory_notes(self, user_text: str) -> bool:
        lowered = user_text.casefold()
        triggers = [
            "помнишь",
            "запомнил",
            "запомнить",
            "что я просил",
            "что я просил тебя",
            "что я сказал",
            "что ты записал",
            "что ты запомнил",
            "что ты сохранил",
            "что нужно было запомнить",
            "какое слово",
            "заметк",
            "напомни",
            "вспомни",
            "что у меня в заметках",
            "что в заметках",
        ]
        return any(trigger in lowered for trigger in triggers)
