from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LeadFieldValueRead(BaseModel):
    field_key: str
    value_raw: str | None
    value_normalized: str | None
    confidence: float | None

    class Config:
        from_attributes = True


class LeadRead(BaseModel):
    id: int
    bot_id: int
    conversation_id: int
    end_user_id: int
    lead_type: str | None
    status: str
    summary: str | None
    created_at: datetime
    updated_at: datetime
    field_values: list[LeadFieldValueRead] = []

    class Config:
        from_attributes = True
