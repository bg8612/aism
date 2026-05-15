from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.bot_prompt import BotPrompt


DEFAULT_PROMPTS: dict[str, tuple[str, str]] = {
    "manager_system": (
        "Main manager system prompt",
        settings.openrouter_business_manager_prompt,
    ),
    "knowledge_answer": (
        "Knowledge base answer prompt",
        "Answer using relevant knowledge base facts. If details are missing, provide useful general guidance and say you will verify details with colleagues.",
    ),
    "lead_collection": (
        "Lead collection prompt",
        "If user is ready, collect name, phone, service, and preferred time in a concise manager style.",
    ),
    "fallback": (
        "Fallback response prompt",
        "If exact answer is not available, respond briefly, ask a clarifying question, and say you will verify details.",
    ),
    "manager_transfer": (
        "Manager handoff prompt",
        "If additional validation is needed, say you will check with colleagues and return with details.",
    ),
}


class BotPromptRepository:
    async def list_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[BotPrompt]:
        result = await session.scalars(
            select(BotPrompt).where(BotPrompt.bot_id == bot_id).order_by(BotPrompt.prompt_key.asc(), BotPrompt.id.asc())
        )
        return list(result.all())

    async def get_by_id(self, session: AsyncSession, *, prompt_id: int) -> BotPrompt | None:
        return await session.get(BotPrompt, prompt_id)

    async def get_by_bot_id_and_key(self, session: AsyncSession, *, bot_id: int, prompt_key: str) -> BotPrompt | None:
        statement = (
            select(BotPrompt)
            .where(BotPrompt.bot_id == bot_id)
            .where(BotPrompt.prompt_key == prompt_key)
            .limit(1)
        )
        return await session.scalar(statement)

    async def get_or_create_defaults(self, session: AsyncSession, *, bot_id: int) -> list[BotPrompt]:
        existing = await self.list_by_bot_id(session, bot_id=bot_id)
        by_key = {item.prompt_key: item for item in existing}
        for prompt_key, (title, content) in DEFAULT_PROMPTS.items():
            if prompt_key in by_key:
                continue
            item = BotPrompt(
                bot_id=bot_id,
                prompt_key=prompt_key,
                title=title,
                content=content,
                is_active=True,
            )
            session.add(item)
            await session.flush()
            by_key[prompt_key] = item
        return [by_key[key] for key in sorted(by_key.keys())]

    async def update(self, session: AsyncSession, *, prompt: BotPrompt, **values: object) -> BotPrompt:
        for key, value in values.items():
            if value is None:
                continue
            if hasattr(prompt, key):
                setattr(prompt, key, value)
        await session.flush()
        return prompt
