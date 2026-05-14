from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_field import BotField


class BotFieldRepository:
    async def list_active_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[BotField]:
        statement = (
            select(BotField)
            .where(BotField.bot_id == bot_id)
            .where(BotField.is_active.is_(True))
            .order_by(BotField.order_index.asc(), BotField.id.asc())
        )
        result = await session.scalars(statement)
        return list(result.all())

    async def list_required_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[BotField]:
        statement = (
            select(BotField)
            .where(BotField.bot_id == bot_id)
            .where(BotField.is_active.is_(True))
            .where(BotField.is_required.is_(True))
            .order_by(BotField.order_index.asc(), BotField.id.asc())
        )
        result = await session.scalars(statement)
        return list(result.all())
