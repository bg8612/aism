from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base_mixins import TimestampMixin


class Bot(TimestampMixin, Base):
    __tablename__ = "bots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    telegram_bot_username: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    client = relationship("Client", back_populates="bots")
    end_users = relationship("EndUser", back_populates="bot")
    conversations = relationship("Conversation", back_populates="bot")
    messages = relationship("Message", back_populates="bot")
    leads = relationship("Lead", back_populates="bot")
    settings = relationship("BotSettings", back_populates="bot", uselist=False)
    knowledge_blocks = relationship("KnowledgeBlock", back_populates="bot")
    bot_fields = relationship("BotField", back_populates="bot")
    bot_questions = relationship("BotQuestion", back_populates="bot")
    human_questions = relationship("HumanQuestion", back_populates="bot")
    channels = relationship("BotChannel", back_populates="bot")
