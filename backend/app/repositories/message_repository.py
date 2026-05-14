from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


class MessageRepository:
    async def create(
        self,
        session: AsyncSession,
        *,
        conversation_id: int,
        bot_id: int,
        end_user_id: int,
        sender_type: str,
        message_text: str,
        raw_payload_json: dict[str, Any] | None = None,
    ) -> Message:
        message = Message(
            conversation_id=conversation_id,
            bot_id=bot_id,
            end_user_id=end_user_id,
            sender_type=sender_type,
            message_text=message_text,
            raw_payload_json=raw_payload_json,
        )
        session.add(message)
        await session.flush()
        return message

    async def list_recent_for_context(
        self,
        session: AsyncSession,
        *,
        conversation_id: int,
        limit: int,
    ) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        result = await session.scalars(statement)
        messages = list(result.all())
        messages.reverse()
        return messages
