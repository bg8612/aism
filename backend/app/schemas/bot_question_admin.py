from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BotQuestionCreate(BaseModel):
    field_id: int
    question_text: str = Field(min_length=1)
    is_required: bool = True
    order_index: int = 0
    is_active: bool = True


class BotQuestionUpdate(BaseModel):
    field_id: int | None = None
    question_text: str | None = None
    is_required: bool | None = None
    order_index: int | None = None
    is_active: bool | None = None


class BotQuestionRead(BaseModel):
    id: int
    bot_id: int
    field_id: int
    question_text: str
    is_required: bool
    order_index: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
