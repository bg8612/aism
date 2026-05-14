from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeBlockCreate(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    is_active: bool = True


class KnowledgeBlockUpdate(BaseModel):
    category: str | None = None
    title: str | None = None
    content: str | None = None
    is_active: bool | None = None


class KnowledgeBlockRead(BaseModel):
    id: int
    bot_id: int
    category: str
    title: str
    content: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
