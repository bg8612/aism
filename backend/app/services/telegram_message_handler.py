from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.repositories.human_question_repository import HumanQuestionRepository
from app.services.ai_response_parser import AIManagerResult, AIResponseParser
from app.services.business_context_service import BusinessContext, BusinessContextService
from app.services.dialogue_storage_service import DialogueContext, DialogueStorageService
from app.services.lead_processing_service import LeadProcessingService
from app.services.openrouter_client import OpenRouterClient
from app.services.telegram_client import TelegramClient
from app.services.telegram_waiting_indicator import TelegramWaitingIndicator
from app.services.topic_filter_service import TopicFilterService

logger = logging.getLogger(__name__)

GENERIC_TEMPORARY_ERROR = "Сервис временно недоступен. Попробуйте еще раз через минуту."
GENERIC_EMPTY_ERROR = "Сервис временно недоступен. Попробуйте еще раз позже."


class TelegramMessageHandler:
    def __init__(
        self,
        telegram_client: TelegramClient,
        openrouter_client: OpenRouterClient,
        dialogue_storage_service: DialogueStorageService | None = None,
        business_context_service: BusinessContextService | None = None,
        topic_filter_service: TopicFilterService | None = None,
        ai_response_parser: AIResponseParser | None = None,
        lead_processing_service: LeadProcessingService | None = None,
        human_question_repository: HumanQuestionRepository | None = None,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
    ) -> None:
        self._telegram_client = telegram_client
        self._openrouter_client = openrouter_client
        self._dialogue_storage_service = dialogue_storage_service or DialogueStorageService()
        self._business_context_service = business_context_service or BusinessContextService()
        self._topic_filter_service = topic_filter_service or TopicFilterService()
        self._ai_response_parser = ai_response_parser or AIResponseParser()
        self._lead_processing_service = lead_processing_service or LeadProcessingService()
        self._human_question_repository = human_question_repository or HumanQuestionRepository()
        self._session_factory = session_factory

    async def handle_telegram_message(
        self,
        *,
        update: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        chat_id, message_id, user_text = self._extract_text_payload(update)
        if chat_id is None or not user_text:
            return {"ok": True, "skipped": "no_text_message"}

        dialogue_context = await self._dialogue_storage_service.save_user_message_from_telegram(
            update=update,
            user_text=user_text,
        )
        model_context = await self._dialogue_storage_service.get_model_context(
            context=dialogue_context,
            user_text=user_text,
        )
        business_context = await self._business_context_service.get_business_context(
            dialogue_context=dialogue_context,
            user_text=user_text,
        )

        if business_context is None:
            reply = await self._generate_legacy_reply(
                chat_id=chat_id,
                message_id=message_id,
                user_text=user_text,
                conversation_messages=model_context.conversation_messages,
                memory_notes=model_context.memory_notes,
            )
            await self._finalize_reply(
                chat_id=chat_id,
                message_id=message_id,
                dialogue_context=dialogue_context,
                reply=reply,
                source=source,
            )
            return {"ok": True, "mode": "legacy_fallback"}

        filter_result = self._topic_filter_service.evaluate(user_text=user_text, business_context=business_context)
        if not filter_result.is_allowed:
            reply = filter_result.reply_if_rejected or business_context.bot_settings.offtopic_message
            await self._finalize_reply(
                chat_id=chat_id,
                message_id=message_id,
                dialogue_context=dialogue_context,
                reply=reply,
                source=source,
            )
            return {"ok": True, "mode": "topic_filter", "reason": filter_result.reason}

        waiting_indicator = TelegramWaitingIndicator(self._telegram_client)
        await waiting_indicator.start(chat_id=chat_id, reply_to_message_id=message_id)
        try:
            raw_manager_response = await self._openrouter_client.generate_business_manager_response(
                user_text=user_text,
                conversation_messages=model_context.conversation_messages,
                memory_notes=model_context.memory_notes,
                business_context=business_context,
                knowledge_blocks=business_context.knowledge_blocks,
                current_lead_data=business_context.current_lead_data(),
                missing_required_fields=[field.field_key for field in business_context.required_missing_fields],
            )
        except Exception:
            logger.exception("Business manager response failed")
            raw_manager_response = ""
        finally:
            await waiting_indicator.stop()

        ai_result = self._ai_response_parser.parse_manager_response(
            raw_manager_response,
            fallback_reply=business_context.bot_settings.fallback_message,
        )
        reply = self._build_final_reply(ai_result=ai_result, business_context=business_context)

        lead_result = await self._lead_processing_service.process_ai_result(
            dialogue_context=dialogue_context,
            business_context=business_context,
            ai_result=ai_result,
        )

        if ai_result.needs_human and dialogue_context is not None:
            await self._create_human_question(
                dialogue_context=dialogue_context,
                question_text=user_text,
                reason=ai_result.human_question_reason or "needs_manager_confirmation",
                lead_id=lead_result.lead.id if lead_result.lead is not None else None,
            )
            if not ai_result.reply.strip():
                reply = business_context.bot_settings.human_transfer_message

        if lead_result.next_question and lead_result.next_question not in reply and not lead_result.completed:
            reply = f"{reply}\n\n{lead_result.next_question}".strip()

        await self._finalize_reply(
            chat_id=chat_id,
            message_id=message_id,
            dialogue_context=dialogue_context,
            reply=reply,
            source=source,
        )
        return {"ok": True, "mode": "business_manager", "intent": ai_result.intent}

    async def _generate_legacy_reply(
        self,
        *,
        chat_id: int,
        message_id: int | None,
        user_text: str,
        conversation_messages: list[dict[str, str]],
        memory_notes: list[str],
    ) -> str:
        waiting_indicator = TelegramWaitingIndicator(self._telegram_client)
        await waiting_indicator.start(chat_id=chat_id, reply_to_message_id=message_id)
        try:
            return await self._openrouter_client.generate_reply(
                user_text,
                conversation_messages=conversation_messages,
                memory_notes=memory_notes,
            )
        except Exception:
            logger.exception("Legacy OpenRouter response failed")
            return GENERIC_TEMPORARY_ERROR
        finally:
            await waiting_indicator.stop()

    async def _create_human_question(
        self,
        *,
        dialogue_context: DialogueContext,
        question_text: str,
        reason: str,
        lead_id: int | None,
    ) -> None:
        async with self._session_factory() as session:
            try:
                await self._human_question_repository.create_human_question(
                    session,
                    bot_id=dialogue_context.bot_id,
                    conversation_id=dialogue_context.conversation_id,
                    end_user_id=dialogue_context.end_user_id,
                    question_text=question_text,
                    reason=reason,
                    lead_id=lead_id,
                )
                await session.commit()
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Database error while creating human question")
            except Exception:
                await session.rollback()
                logger.exception("Unexpected error while creating human question")

    async def _finalize_reply(
        self,
        *,
        chat_id: int,
        message_id: int | None,
        dialogue_context: DialogueContext | None,
        reply: str,
        source: str,
    ) -> None:
        safe_reply = reply.strip()[: settings.bot_reply_max_chars] or GENERIC_EMPTY_ERROR
        await self._dialogue_storage_service.save_bot_reply(
            context=dialogue_context,
            reply_text=safe_reply,
            raw_payload_json={"source": source},
        )
        await self._telegram_client.send_message(
            chat_id=chat_id,
            text=safe_reply,
            reply_to_message_id=message_id,
        )

    def _build_final_reply(self, *, ai_result: AIManagerResult, business_context: BusinessContext) -> str:
        reply = self._openrouter_client.sanitize_manager_reply(
            ai_result.reply,
            fallback_message=business_context.bot_settings.fallback_message,
        )
        if not ai_result.is_on_topic:
            return business_context.bot_settings.offtopic_message
        if ai_result.needs_human and not reply.strip():
            return business_context.bot_settings.human_transfer_message
        return reply

    def _extract_text_payload(self, update: dict[str, Any]) -> tuple[int | None, int | None, str | None]:
        message = update.get("message") or update.get("edited_message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")
        message_id = message.get("message_id")
        text = message.get("text") or message.get("caption")
        if isinstance(chat_id, int) and isinstance(text, str):
            normalized = text.strip()
            return chat_id, message_id if isinstance(message_id, int) else None, normalized or None
        return None, None, None
