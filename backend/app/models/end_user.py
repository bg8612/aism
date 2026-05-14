from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class EndUser(TimestampMixin, Base):
    __tablename__ = "end_users"
    __table_args__ = (
        UniqueConstraint("bot_id", "channel", "external_user_id", name="uq_end_users_bot_channel_external"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    external_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    bot = relationship("Bot", back_populates="end_users")
    conversations = relationship("Conversation", back_populates="end_user")
    messages = relationship("Message", back_populates="end_user")
    leads = relationship("Lead", back_populates="end_user")
