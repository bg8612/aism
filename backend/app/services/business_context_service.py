from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.models.bot import Bot
from app.models.bot_field import BotField
from app.models.bot_prompt import BotPrompt
from app.models.bot_question import BotQuestion
from app.models.bot_settings import BotSettings
from app.models.knowledge_block import KnowledgeBlock
from app.models.lead import Lead
from app.repositories.bot_field_repository import BotFieldRepository
from app.repositories.bot_question_repository import BotQuestionRepository
from app.repositories.bot_prompt_repository import BotPromptRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.bot_settings_repository import BotSettingsRepository
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.lead_repository import LeadRepository
from app.services.dialogue_storage_service import DialogueContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BusinessContext:
    bot: Bot
    bot_settings: BotSettings
    knowledge_blocks: list[KnowledgeBlock]
    bot_fields: list[BotField]
    bot_questions: list[BotQuestion]
    prompts: list[BotPrompt]
    current_lead: Lead | None
    required_missing_fields: list[BotField]

    def current_lead_data(self) -> dict[str, str]:
        if self.current_lead is None:
            return {}
        values: dict[str, str] = {}
        for field_value in self.current_lead.field_values:
            value = field_value.value_normalized or field_value.value_raw
            if value:
                values[field_value.field_key] = value
        return values


class BusinessContextService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] = AsyncSessionLocal,
        bot_repository: BotRepository | None = None,
        bot_settings_repository: BotSettingsRepository | None = None,
        knowledge_repository: KnowledgeRepository | None = None,
        bot_field_repository: BotFieldRepository | None = None,
        bot_question_repository: BotQuestionRepository | None = None,
        bot_prompt_repository: BotPromptRepository | None = None,
        lead_repository: LeadRepository | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._bot_repository = bot_repository or BotRepository()
        self._bot_settings_repository = bot_settings_repository or BotSettingsRepository()
        self._knowledge_repository = knowledge_repository or KnowledgeRepository()
        self._bot_field_repository = bot_field_repository or BotFieldRepository()
        self._bot_question_repository = bot_question_repository or BotQuestionRepository()
        self._bot_prompt_repository = bot_prompt_repository or BotPromptRepository()
        self._lead_repository = lead_repository or LeadRepository()

    async def get_business_context(
        self,
        *,
        dialogue_context: DialogueContext | None,
        user_text: str,
    ) -> BusinessContext | None:
        if dialogue_context is None:
            return None

        async with self._session_factory() as session:
            try:
                bot = await self._bot_repository.get_by_id(session, bot_id=dialogue_context.bot_id)
                if bot is None:
                    return None

                bot_settings = await self._bot_settings_repository.get_or_create_by_bot_id(
                    session,
                    bot_id=bot.id,
                    business_name=bot.name,
                )
                knowledge_blocks = await self._knowledge_repository.search_relevant_blocks(
                    session,
                    bot_id=bot.id,
                    message_text=user_text,
                    limit=settings.openrouter_business_knowledge_limit,
                )
                bot_fields = await self._bot_field_repository.list_active_by_bot_id(session, bot_id=bot.id)
                bot_questions = await self._bot_question_repository.list_active_by_bot_id(session, bot_id=bot.id)
                prompts = await self._bot_prompt_repository.get_or_create_defaults(session, bot_id=bot.id)
                current_lead = await self._lead_repository.get_active_draft_by_conversation_id(
                    session,
                    conversation_id=dialogue_context.conversation_id,
                )
                required_missing_fields = self._get_required_missing_fields(bot_fields=bot_fields, lead=current_lead)
                await session.commit()
                return BusinessContext(
                    bot=bot,
                    bot_settings=bot_settings,
                    knowledge_blocks=knowledge_blocks,
                    bot_fields=bot_fields,
                    bot_questions=bot_questions,
                    prompts=prompts,
                    current_lead=current_lead,
                    required_missing_fields=required_missing_fields,
                )
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Database error while building business context")
            except Exception:
                await session.rollback()
                logger.exception("Unexpected error while building business context")

        return None

    def _get_required_missing_fields(self, *, bot_fields: list[BotField], lead: Lead | None) -> list[BotField]:
        required_fields = [field for field in bot_fields if field.is_required]
        if lead is None:
            return required_fields

        filled = {
            item.field_key
            for item in lead.field_values
            if (item.value_normalized and item.value_normalized.strip()) or (item.value_raw and item.value_raw.strip())
        }
        return [field for field in required_fields if field.field_key not in filled]
