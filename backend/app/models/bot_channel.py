from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class BotChannel(TimestampMixin, Base):
    __tablename__ = "bot_channels"
    __table_args__ = (
        UniqueConstraint("bot_id", "channel_type", name="uq_bot_channels_bot_channel_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    bot_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    bot_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    bot = relationship("Bot", back_populates="channels")
