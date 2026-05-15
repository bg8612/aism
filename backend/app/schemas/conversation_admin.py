from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConversationListItem(BaseModel):
    id: int
    bot_id: int
    end_user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    last_message_at: datetime | None
    status: str
    summary: str | None
    has_lead: bool
    has_human_question: bool


class ConversationMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_type: str
    message_text: str
    created_at: datetime


class ConversationDetailRead(BaseModel):
    id: int
    bot_id: int
    end_user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    status: str
    summary: str | None
    last_message_at: datetime | None
    messages: list[ConversationMessageRead]


class AdminSendMessageRequest(BaseModel):
    text: str
