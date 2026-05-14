from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bot_field import BotField
from app.models.bot_question import BotQuestion


class BotQuestionRepository:
    async def list_active_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[BotQuestion]:
        statement = (
            select(BotQuestion)
            .options(selectinload(BotQuestion.field))
            .where(BotQuestion.bot_id == bot_id)
            .where(BotQuestion.is_active.is_(True))
            .order_by(BotQuestion.order_index.asc(), BotQuestion.id.asc())
        )
        result = await session.scalars(statement)
        return list(result.all())

    async def get_question_for_field(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        field_key: str,
    ) -> BotQuestion | None:
        statement = (
            select(BotQuestion)
            .join(BotField, BotQuestion.field_id == BotField.id)
            .options(selectinload(BotQuestion.field))
            .where(BotQuestion.bot_id == bot_id)
            .where(BotQuestion.is_active.is_(True))
            .where(BotField.field_key == field_key)
            .order_by(BotQuestion.order_index.asc(), BotQuestion.id.asc())
            .limit(1)
        )
        return await session.scalar(statement)
