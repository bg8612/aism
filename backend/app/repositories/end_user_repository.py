from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.end_user import EndUser


class EndUserRepository:
    async def get_or_create(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        channel: str,
        external_user_id: str,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> EndUser:
        statement = (
            select(EndUser)
            .where(EndUser.bot_id == bot_id)
            .where(EndUser.channel == channel)
            .where(EndUser.external_user_id == external_user_id)
            .limit(1)
        )
        end_user = await session.scalar(statement)

        if end_user is not None:
            end_user.username = username
            end_user.first_name = first_name
            end_user.last_name = last_name
            return end_user

        end_user = EndUser(
            bot_id=bot_id,
            channel=channel,
            external_user_id=external_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        session.add(end_user)
        await session.flush()
        return end_user
