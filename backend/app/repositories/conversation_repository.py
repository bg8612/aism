from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation


class ConversationRepository:
    async def list_by_bot_id(self, session: AsyncSession, *, bot_id: int, limit: int = 200) -> list[Conversation]:
        statement = (
            select(Conversation)
            .options(selectinload(Conversation.end_user))
            .where(Conversation.bot_id == bot_id)
            .order_by(desc(Conversation.last_message_at), desc(Conversation.updated_at), desc(Conversation.id))
            .limit(limit)
        )
        result = await session.scalars(statement)
        return list(result.all())

    async def get_by_id(self, session: AsyncSession, *, conversation_id: int) -> Conversation | None:
        statement = (
            select(Conversation)
            .options(selectinload(Conversation.end_user))
            .where(Conversation.id == conversation_id)
            .limit(1)
        )
        return await session.scalar(statement)

    async def get_or_create_active(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        end_user_id: int,
        channel: str,
    ) -> Conversation:
        statement = (
            select(Conversation)
            .where(Conversation.bot_id == bot_id)
            .where(Conversation.end_user_id == end_user_id)
            .where(Conversation.channel == channel)
            .where(Conversation.status == "active")
            .order_by(desc(Conversation.updated_at))
            .limit(1)
        )
        conversation = await session.scalar(statement)
        if conversation is not None:
            return conversation

        conversation = Conversation(bot_id=bot_id, end_user_id=end_user_id, channel=channel, status="active")
        session.add(conversation)
        await session.flush()
        return conversation

    async def touch_last_message(self, session: AsyncSession, *, conversation: Conversation) -> None:
        conversation.last_message_at = datetime.now(timezone.utc)
