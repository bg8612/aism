from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bot_field import BotField
from app.models.bot_question import BotQuestion


class BotQuestionRepository:
    async def list_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[BotQuestion]:
        statement = (
            select(BotQuestion)
            .options(selectinload(BotQuestion.field))
            .where(BotQuestion.bot_id == bot_id)
            .order_by(BotQuestion.order_index.asc(), BotQuestion.id.asc())
        )
        result = await session.scalars(statement)
        return list(result.all())

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

    async def get_by_id(self, session: AsyncSession, *, question_id: int) -> BotQuestion | None:
        statement = (
            select(BotQuestion)
            .options(selectinload(BotQuestion.field))
            .where(BotQuestion.id == question_id)
            .limit(1)
        )
        return await session.scalar(statement)

    async def create(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        field_id: int,
        question_text: str,
        is_required: bool,
        order_index: int,
        is_active: bool,
    ) -> BotQuestion:
        question = BotQuestion(
            bot_id=bot_id,
            field_id=field_id,
            question_text=question_text,
            is_required=is_required,
            order_index=order_index,
            is_active=is_active,
        )
        session.add(question)
        await session.flush()
        return question

    async def update(self, session: AsyncSession, *, question: BotQuestion, **values: object) -> BotQuestion:
        for key, value in values.items():
            if value is None:
                continue
            if hasattr(question, key):
                setattr(question, key, value)
        await session.flush()
        return question

    async def deactivate(self, session: AsyncSession, *, question: BotQuestion) -> BotQuestion:
        question.is_active = False
        await session.flush()
        return question
