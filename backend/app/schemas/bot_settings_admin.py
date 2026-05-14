from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BotSettingsUpdate(BaseModel):
    business_name: str | None = None
    business_description: str | None = None
    allowed_topics: str | None = None
    forbidden_topics: str | None = None
    offtopic_message: str | None = None
    fallback_message: str | None = None
    human_transfer_message: str | None = None
    answer_only_from_knowledge_base: bool | None = None
    collect_leads: bool | None = None


class BotSettingsRead(BaseModel):
    id: int
    bot_id: int
    business_name: str
    business_description: str | None
    allowed_topics: str | None
    forbidden_topics: str | None
    offtopic_message: str
    fallback_message: str
    human_transfer_message: str
    answer_only_from_knowledge_base: bool
    collect_leads: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
