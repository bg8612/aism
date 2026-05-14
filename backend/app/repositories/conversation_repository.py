from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation


class ConversationRepository:
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
