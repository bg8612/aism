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

    def _active_statement(self, *, bot_id: int) -> Select[tuple[KnowledgeBlock]]:
        return (
            select(KnowledgeBlock)
            .where(KnowledgeBlock.bot_id == bot_id)
            .where(KnowledgeBlock.is_active.is_(True))
            .order_by(KnowledgeBlock.category.asc(), KnowledgeBlock.id.asc())
        )

    def _tokenize(self, text: str) -> list[str]:
        tokens = re.findall(r"[A-Za-zА-Яа-я0-9]{3,}", text.casefold())
        seen: set[str] = set()
        result: list[str] = []
        for token in tokens:
            if token in seen:
                continue
            seen.add(token)
            result.append(token)
        return result
