from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bot_channel import BotChannel


class BotChannelRepository:
    async def get_by_bot_id_and_channel(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        channel_type: str,
    ) -> BotChannel | None:
        statement = (
            select(BotChannel)
            .where(BotChannel.bot_id == bot_id)
            .where(BotChannel.channel_type == channel_type)
            .limit(1)
        )
        return await session.scalar(statement)

    async def create_or_update_channel(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        channel_type: str,
        bot_token_encrypted: str,
        bot_username: str | None,
        webhook_secret: str | None,
        is_active: bool = True,
    ) -> BotChannel:
        channel = await self.get_by_bot_id_and_channel(session, bot_id=bot_id, channel_type=channel_type)
        if channel is None:
            channel = BotChannel(
                bot_id=bot_id,
                channel_type=channel_type,
                bot_token_encrypted=bot_token_encrypted,
                bot_username=bot_username,
                webhook_secret=webhook_secret,
                is_active=is_active,
            )
            session.add(channel)
            await session.flush()
            return channel

        channel.bot_token_encrypted = bot_token_encrypted
        channel.bot_username = bot_username
        channel.webhook_secret = webhook_secret
        channel.is_active = is_active
        await session.flush()
        return channel

    async def deactivate_channel(self, session: AsyncSession, *, channel: BotChannel) -> BotChannel:
        channel.is_active = False
        await session.flush()
        return channel
