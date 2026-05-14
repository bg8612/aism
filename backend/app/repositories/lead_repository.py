from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lead import Lead
from app.models.lead_field_value import LeadFieldValue


class LeadRepository:
    async def list_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[Lead]:
        statement = (
            select(Lead)
            .options(selectinload(Lead.field_values))
            .where(Lead.bot_id == bot_id)
            .order_by(Lead.created_at.desc(), Lead.id.desc())
        )
        result = await session.scalars(statement)
        return list(result.all())

    async def get_active_draft_by_conversation_id(
        self,
        session: AsyncSession,
        *,
        conversation_id: int,
    ) -> Lead | None:
        statement = (
            select(Lead)
            .options(selectinload(Lead.field_values))
            .where(Lead.conversation_id == conversation_id)
            .where(Lead.status.in_(("draft", "new", "in_progress")))
            .order_by(Lead.updated_at.desc(), Lead.id.desc())
            .limit(1)
        )
        return await session.scalar(statement)

    async def create_draft_lead(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        conversation_id: int,
        end_user_id: int,
        lead_type: str | None = None,
        summary: str | None = None,
    ) -> Lead:
        lead = Lead(
            bot_id=bot_id,
            conversation_id=conversation_id,
            end_user_id=end_user_id,
            lead_type=lead_type,
            status="draft",
            summary=summary,
        )
        session.add(lead)
        await session.flush()
        return lead

    async def update_lead_summary(self, session: AsyncSession, *, lead: Lead, summary: str | None) -> Lead:
        lead.summary = summary
        await session.flush()
        return lead

    async def upsert_lead_field_value(
        self,
        session: AsyncSession,
        *,
        lead: Lead,
        field_key: str,
        value_raw: str | None,
        value_normalized: str | None,
        confidence: float | None,
    ) -> LeadFieldValue:
        existing = next((item for item in lead.field_values if item.field_key == field_key), None)
        if existing is not None:
            existing.value_raw = value_raw
            existing.value_normalized = value_normalized
            existing.confidence = confidence
            await session.flush()
            return existing

        field_value = LeadFieldValue(
            lead_id=lead.id,
            field_key=field_key,
            value_raw=value_raw,
            value_normalized=value_normalized,
            confidence=confidence,
        )
        session.add(field_value)
        lead.field_values.append(field_value)
        await session.flush()
        return field_value

    async def mark_lead_completed_if_required_fields_filled(
        self,
        session: AsyncSession,
        *,
        lead: Lead,
        required_field_keys: Iterable[str],
    ) -> bool:
        required_keys = {field_key for field_key in required_field_keys if field_key}
        available_keys = {
            item.field_key
            for item in lead.field_values
            if (item.value_normalized and item.value_normalized.strip()) or (item.value_raw and item.value_raw.strip())
        }
        if required_keys and required_keys.issubset(available_keys):
            lead.status = "completed"
            await session.flush()
            return True

        lead.status = "draft"
        await session.flush()
        return False
