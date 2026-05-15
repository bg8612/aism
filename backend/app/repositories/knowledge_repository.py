from __future__ import annotations

import re

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_block import KnowledgeBlock


class KnowledgeRepository:
    async def list_active_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[KnowledgeBlock]:
        statement = self._active_statement(bot_id=bot_id)
        result = await session.scalars(statement)
        return list(result.all())

    async def search_relevant_blocks(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        message_text: str,
        limit: int = 5,
    ) -> list[KnowledgeBlock]:
        blocks = await self.list_active_by_bot_id(session, bot_id=bot_id)
        if not blocks:
            return []

        query_tokens = self._tokenize(message_text)
        if not query_tokens:
            return blocks[:limit]

        scored_blocks: list[tuple[int, KnowledgeBlock]] = []
        for block in blocks:
            haystack = " ".join([block.category, block.title, block.content]).casefold()
            score = 0
            for token in query_tokens:
                if token in haystack:
                    score += 3
                if token in block.title.casefold():
                    score += 2
                if token in block.category.casefold():
                    score += 1
            if score > 0:
                scored_blocks.append((score, block))

        if not scored_blocks:
            return blocks[:limit]

        scored_blocks.sort(key=lambda item: item[0], reverse=True)
        return [block for _, block in scored_blocks[:limit]]

    async def list_by_bot_id(self, session: AsyncSession, *, bot_id: int) -> list[KnowledgeBlock]:
        result = await session.scalars(
            select(KnowledgeBlock).where(KnowledgeBlock.bot_id == bot_id).order_by(KnowledgeBlock.created_at.desc())
        )
        return list(result.all())

    async def get_by_id(self, session: AsyncSession, *, block_id: int) -> KnowledgeBlock | None:
        return await session.get(KnowledgeBlock, block_id)

    async def create(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        category: str,
        title: str,
        content: str,
        is_active: bool = True,
    ) -> KnowledgeBlock:
        block = KnowledgeBlock(
            bot_id=bot_id,
            category=category,
            title=title,
            content=content,
            is_active=is_active,
        )
        session.add(block)
        await session.flush()
        return block

    async def update(self, session: AsyncSession, *, block: KnowledgeBlock, **values: object) -> KnowledgeBlock:
        for key, value in values.items():
            if value is None:
                continue
            if hasattr(block, key):
                setattr(block, key, value)
        await session.flush()
        return block

    async def deactivate(self, session: AsyncSession, *, block: KnowledgeBlock) -> KnowledgeBlock:
        block.is_active = False
        await session.flush()
        return block

    def _active_statement(self, *, bot_id: int) -> Select[tuple[KnowledgeBlock]]:
        return (
            select(KnowledgeBlock)
            .where(KnowledgeBlock.bot_id == bot_id)
            .where(KnowledgeBlock.is_active.is_(True))
            .order_by(KnowledgeBlock.category.asc(), KnowledgeBlock.id.asc())
        )

    def _tokenize(self, text: str) -> list[str]:
        tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", text.casefold())
        seen: set[str] = set()
        result: list[str] = []
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            result.append(token)
        return result
