from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import Bot


class BotRepository:
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
