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

    async def has_newer_user_message(
        self,
        session: AsyncSession,
        *,
        conversation_id: int,
        after_message_id: int,
    ) -> bool:
        statement = (
            select(Message.id)
            .where(Message.conversation_id == conversation_id)
            .where(Message.sender_type == "user")
            .where(Message.id > after_message_id)
            .limit(1)
        )
        found = await session.scalar(statement)
        return found is not None

    async def list_for_conversation(
        self,
        session: AsyncSession,
        *,
        conversation_id: int,
        limit: int = 500,
    ) -> list[Message]:
        statement = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc(), Message.id.asc())
            .limit(limit)
        )
        result = await session.scalars(statement)
        return list(result.all())
