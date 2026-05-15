from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BotPromptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bot_id: int
    prompt_key: str
    title: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BotPromptUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    is_active: bool | None = None
