from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from app.repositories.bot_question_repository import BotQuestionRepository
from app.repositories.lead_repository import LeadRepository
from app.services.ai_response_parser import AIManagerResult
from app.services.business_context_service import BusinessContext
from app.services.dialogue_storage_service import DialogueContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LeadProcessingResult:
    lead: Lead | None
    next_question: str | None
    completed: bool


class LeadProcessingService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
        lead_repository: LeadRepository | None = None,
        bot_question_repository: BotQuestionRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._lead_repository = lead_repository or LeadRepository()
        self._bot_question_repository = bot_question_repository or BotQuestionRepository()

    async def process_ai_result(
        self,
        *,
        dialogue_context: DialogueContext | None,
        business_context: BusinessContext | None,
        ai_result: AIManagerResult,
    ) -> LeadProcessingResult:
        if dialogue_context is None or business_context is None:
            return LeadProcessingResult(lead=None, next_question=None, completed=False)

        if not business_context.bot_settings.collect_leads:
            return LeadProcessingResult(lead=business_context.current_lead, next_question=None, completed=False)

        has_fields = any(value for value in ai_result.lead_fields.values())
        should_touch_lead = ai_result.lead_action != "none" or has_fields
        if not should_touch_lead:
            return LeadProcessingResult(lead=business_context.current_lead, next_question=None, completed=False)

        async with self._session_factory() as session:
            try:
                lead = await self._lead_repository.get_active_draft_by_conversation_id(
                    session,
                    conversation_id=dialogue_context.conversation_id,
                )
                if lead is None:
                    lead = await self._lead_repository.create_draft_lead(
                        session,
                        bot_id=dialogue_context.bot_id,
                        conversation_id=dialogue_context.conversation_id,
                        end_user_id=dialogue_context.end_user_id,
                        lead_type=ai_result.intent,
                    )

                allowed_field_keys = {field.field_key for field in business_context.bot_fields}
                for field_key, raw_value in ai_result.lead_fields.items():
                    if field_key not in allowed_field_keys:
                        continue
                    if not raw_value:
                        continue
                    normalized_value = self._normalize_field_value(field_key=field_key, raw_value=raw_value)
                    await self._lead_repository.upsert_lead_field_value(
                        session,
                        lead=lead,
                        field_key=field_key,
                        value_raw=raw_value,
                        value_normalized=normalized_value,
                        confidence=ai_result.confidence or None,
                    )

                summary = self._build_summary(lead=lead, business_context=business_context)
                await self._lead_repository.update_lead_summary(session, lead=lead, summary=summary)

                required_field_keys = [field.field_key for field in business_context.bot_fields if field.is_required]
                completed = await self._lead_repository.mark_lead_completed_if_required_fields_filled(
                    session,
                    lead=lead,
                    required_field_keys=required_field_keys,
                )
                next_question = None if completed else await self._get_next_question(session, lead=lead, business_context=business_context)
                await session.commit()
                return LeadProcessingResult(lead=lead, next_question=next_question, completed=completed)
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Database error while processing lead result")
            except Exception:
                await session.rollback()
                logger.exception("Unexpected error while processing lead result")

        return LeadProcessingResult(lead=business_context.current_lead, next_question=None, completed=False)

    async def _get_next_question(
        self,
        session: AsyncSession,
        *,
        lead: Lead,
        business_context: BusinessContext,
    ) -> str | None:
        filled_keys = {
            item.field_key
            for item in lead.field_values
            if (item.value_normalized and item.value_normalized.strip()) or (item.value_raw and item.value_raw.strip())
        }
        for field in business_context.bot_fields:
            if not field.is_required or field.field_key in filled_keys:
                continue
            question = await self._bot_question_repository.get_question_for_field(
                session,
                bot_id=business_context.bot.id,
                field_key=field.field_key,
            )
            if question is not None:
                return question.question_text
        return None

    def _normalize_field_value(self, *, field_key: str, raw_value: str) -> str:
        value = raw_value.strip()
        if field_key == "phone":
            digits = re.sub(r"\D", "", value)
            if len(digits) == 11 and digits.startswith("8"):
                digits = "7" + digits[1:]
            if len(digits) == 11 and digits.startswith("7"):
                return f"+7 {digits[1:4]} {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
            if len(digits) == 10:
                return f"+7 {digits[0:3]} {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
        return value

    def _build_summary(self, *, lead: Lead, business_context: BusinessContext) -> str | None:
        if not lead.field_values:
            return None
        labels = {field.field_key: field.label for field in business_context.bot_fields}
        parts: list[str] = []
        for field_value in lead.field_values:
            value = field_value.value_normalized or field_value.value_raw
            if not value:
                continue
            label = labels.get(field_value.field_key, field_value.field_key)
            parts.append(f"{label}: {value}")
        return "; ".join(parts) or None
