from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_settings import BotSettings


class BotSettingsRepository:
    async def get_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> BotSettings | None:
        statement = select(BotSettings).where(BotSettings.bot_id == bot_id).limit(1)
        return await session.scalar(statement)

    async def create_default_for_bot(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        business_name: str = "AISM Business",
    ) -> BotSettings:
        settings = BotSettings(
            bot_id=bot_id,
            business_name=business_name,
            business_description="Бизнес-бот для общения с клиентами в Telegram.",
            allowed_topics="услуги, цены, запись, адрес, график работы, контакты",
            forbidden_topics="домашние задания, программирование, политика, развлечения, личные советы",
            offtopic_message=(
                "Я могу помочь только по вопросам бизнеса: услугам, ценам, записи, адресу, "
                "графику работы и контактам."
            ),
            fallback_message=(
                "У меня нет точной информации по этому вопросу. Я могу зафиксировать вопрос для менеджера."
            ),
            human_transfer_message=(
                "Я зафиксировал ваш вопрос для менеджера. Специалист сможет уточнить информацию."
            ),
            answer_only_from_knowledge_base=True,
            collect_leads=True,
        )
        session.add(settings)
        await session.flush()
        return settings

    async def get_or_create_by_bot_id(self, session: AsyncSession, *, bot_id: int, business_name: str) -> BotSettings:
        settings = await self.get_by_bot_id(session, bot_id=bot_id)
        if settings is not None:
            return settings
        return await self.create_default_for_bot(session, bot_id=bot_id, business_name=business_name)
