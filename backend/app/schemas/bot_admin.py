from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BotCreate(BaseModel):
    client_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    niche: str | None = None
    telegram_token: str | None = None
    telegram_username: str | None = None


class BotUpdate(BaseModel):
    client_id: int | None = None
    name: str | None = None
    is_active: bool | None = None
    telegram_token: str | None = None
    telegram_username: str | None = None


class BotRead(BaseModel):
    id: int
    client_id: int | None
    name: str
    telegram_bot_username: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    has_token: bool = False
    channel_username: str | None = None

    class Config:
        from_attributes = True
