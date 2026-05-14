from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class BotSettings(TimestampMixin, Base):
    __tablename__ = "bot_settings"
    __table_args__ = (
        UniqueConstraint("bot_id", name="uq_bot_settings_bot_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    business_name: Mapped[str] = mapped_column(Text, nullable=False)
    business_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allowed_topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    forbidden_topics: Mapped[str | None] = mapped_column(Text, nullable=True)
    offtopic_message: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_message: Mapped[str] = mapped_column(Text, nullable=False)
    human_transfer_message: Mapped[str] = mapped_column(Text, nullable=False)
    answer_only_from_knowledge_base: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    collect_leads: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    bot = relationship("Bot", back_populates="settings")
