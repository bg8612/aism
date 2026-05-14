from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_field import BotField


class BotFieldRepository:
    async def list_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[BotField]:
        result = await session.scalars(
            select(BotField).where(BotField.bot_id == bot_id).order_by(BotField.order_index.asc(), BotField.id.asc())
        )
        return list(result.all())

    async def list_active_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[BotField]:
        statement = (
            select(BotField)
            .where(BotField.bot_id == bot_id)
            .where(BotField.is_active.is_(True))
            .order_by(BotField.order_index.asc(), BotField.id.asc())
        )
        result = await session.scalars(statement)
        return list(result.all())

    async def get_by_id(self, session: AsyncSession, *, field_id: int) -> BotField | None:
        return await session.get(BotField, field_id)

    async def create(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        field_key: str,
        label: str,
        field_type: str,
        is_required: bool,
        order_index: int,
        validation_type: str | None,
        is_active: bool,
    ) -> BotField:
        field = BotField(
            bot_id=bot_id,
            field_key=field_key,
            label=label,
            field_type=field_type,
            is_required=is_required,
            order_index=order_index,
            validation_type=validation_type,
            is_active=is_active,
        )
        session.add(field)
        await session.flush()
        return field

    async def update(self, session: AsyncSession, *, field: BotField, **values: object) -> BotField:
        for key, value in values.items():
            if value is None:
                continue
            if hasattr(field, key):
                setattr(field, key, value)
        await session.flush()
        return field

    async def deactivate(self, session: AsyncSession, *, field: BotField) -> BotField:
        field.is_active = False
        await session.flush()
        return field

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
