from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot import Bot
from app.models.knowledge_block import KnowledgeBlock


class BotRepository:
    async def resolve_for_global_telegram(
        self,
        session: AsyncSession,
        *,
        preferred_name: str,
        preferred_username: str | None,
    ) -> Bot:
        kb_rows = (
            await session.execute(
                select(Bot, func.count(KnowledgeBlock.id).label("kb_count"))
                .outerjoin(
                    KnowledgeBlock,
                    (KnowledgeBlock.bot_id == Bot.id) & (KnowledgeBlock.is_active.is_(True)),
                )
                .where(Bot.is_active.is_(True))
                .group_by(Bot.id)
                .order_by(func.count(KnowledgeBlock.id).desc(), Bot.created_at.asc(), Bot.id.asc())
            )
        ).all()
        kb_count_by_bot_id = {row.Bot.id: int(row.kb_count or 0) for row in kb_rows}
        best_kb_bot = next((row.Bot for row in kb_rows if int(row.kb_count or 0) > 0), None)

        # 1) Explicit username mapping has top priority.
        if preferred_username:
            by_username = await session.scalar(
                select(Bot).where(Bot.telegram_bot_username == preferred_username).limit(1)
            )
            if by_username is not None:
                if not by_username.is_active:
                    by_username.is_active = True
                if by_username.name != preferred_name:
                    by_username.name = preferred_name
                return by_username

        # 2) Exact bot name match.
        by_name = await session.scalar(select(Bot).where(Bot.name == preferred_name).limit(1))
        if by_name is not None:
            by_name_kb_count = kb_count_by_bot_id.get(by_name.id, 0)
            if by_name_kb_count == 0 and best_kb_bot is not None and best_kb_bot.id != by_name.id:
                return best_kb_bot
            if preferred_username and by_name.telegram_bot_username != preferred_username:
                by_name.telegram_bot_username = preferred_username
            if not by_name.is_active:
                by_name.is_active = True
            return by_name

        # 3) Single active bot: use it (safe default for single-token deployment).
        active_bots = list(
            (
                await session.scalars(
                    select(Bot).where(Bot.is_active.is_(True)).order_by(Bot.created_at.asc(), Bot.id.asc())
                )
            ).all()
        )
        if len(active_bots) == 1:
            return active_bots[0]

        # 4) Pick active bot with the largest active knowledge base.
        if kb_rows and (kb_rows[0].kb_count or 0) > 0:
            return kb_rows[0].Bot

        # 5) Fallback: create new bot record.
        bot = Bot(name=preferred_name, telegram_bot_username=preferred_username, is_active=True)
        session.add(bot)
        await session.flush()
        return bot

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
        return await self.resolve_for_global_telegram(
            session,
            preferred_name=name,
            preferred_username=telegram_bot_username,
        )
