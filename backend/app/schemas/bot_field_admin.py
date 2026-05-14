from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BotFieldCreate(BaseModel):
    field_key: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=255)
    field_type: str = Field(default="text", max_length=50)
    is_required: bool = False
    order_index: int = 0
    validation_type: str | None = None
    is_active: bool = True


class BotFieldUpdate(BaseModel):
    field_key: str | None = None
    label: str | None = None
    field_type: str | None = None
    is_required: bool | None = None
    order_index: int | None = None
    validation_type: str | None = None
    is_active: bool | None = None


class BotFieldRead(BaseModel):
    id: int
    bot_id: int
    field_key: str
    label: str
    field_type: str
    is_required: bool
    order_index: int
    validation_type: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
