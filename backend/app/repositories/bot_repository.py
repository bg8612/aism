from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import Bot


class BotRepository:
    async def list_bots(self, session: AsyncSession) -> list[Bot]:
        result = await session.scalars(select(Bot).order_by(Bot.created_at.desc(), Bot.id.desc()))
        return list(result.all())

    async def get_by_id(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
    ) -> Bot | None:
        statement = select(Bot).where(Bot.id == bot_id).limit(1)
        return await session.scalar(statement)

    async def create_bot(
        self,
        session: AsyncSession,
        *,
        name: str,
        telegram_bot_username: str | None,
        client_id: int | None = None,
        is_active: bool = True,
    ) -> Bot:
        bot = Bot(
            name=name,
            telegram_bot_username=telegram_bot_username,
            client_id=client_id,
            is_active=is_active,
        )
        session.add(bot)
        await session.flush()
        return bot

    async def update_bot(
        self,
        session: AsyncSession,
        *,
        bot: Bot,
        name: str | None = None,
        telegram_bot_username: str | None = None,
        client_id: int | None = None,
        is_active: bool | None = None,
    ) -> Bot:
        if name is not None:
            bot.name = name
        if telegram_bot_username is not None:
            bot.telegram_bot_username = telegram_bot_username
        if client_id is not None:
            bot.client_id = client_id
        if is_active is not None:
            bot.is_active = is_active
        await session.flush()
        return bot

    async def get_or_create_telegram_bot(
        self,
        session: AsyncSession,
        *,
        name: str,
        telegram_bot_username: str | None,
    ) -> Bot:
        statement = select(Bot)
        if telegram_bot_username:
            statement = statement.where(Bot.telegram_bot_username == telegram_bot_username)
        else:
            statement = statement.where(Bot.name == name)

        bot = await session.scalar(statement.limit(1))
        if bot is not None:
            if bot.name != name:
                bot.name = name
            if telegram_bot_username and bot.telegram_bot_username != telegram_bot_username:
                bot.telegram_bot_username = telegram_bot_username
            if not bot.is_active:
                bot.is_active = True
            return bot

        bot = Bot(name=name, telegram_bot_username=telegram_bot_username, is_active=True)
        session.add(bot)
        await session.flush()
        return bot
