from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class HumanQuestionRead(BaseModel):
    id: int
    bot_id: int
    conversation_id: int
    lead_id: int | None
    end_user_id: int
    question_text: str
    reason: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
