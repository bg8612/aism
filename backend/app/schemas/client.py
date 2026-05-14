from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    is_active: bool = True


class ClientUpdate(BaseModel):
    name: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    is_active: bool | None = None


class ClientRead(BaseModel):
    id: int
    name: str
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
