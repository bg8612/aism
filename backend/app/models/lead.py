from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class Lead(TimestampMixin, Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bot_id: Mapped[int] = mapped_column(ForeignKey("bots.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    end_user_id: Mapped[int] = mapped_column(ForeignKey("end_users.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new", server_default="new")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    bot = relationship("Bot", back_populates="leads")
    conversation = relationship("Conversation", back_populates="leads")
    end_user = relationship("EndUser", back_populates="leads")
    field_values = relationship("LeadFieldValue", back_populates="lead")
