from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.human_question import HumanQuestion


class HumanQuestionRepository:
    async def create_human_question(
        self,
        session: AsyncSession,
        *,
        bot_id: int,
        conversation_id: int,
        end_user_id: int,
        question_text: str,
        reason: str,
        lead_id: int | None = None,
        status: str = "new",
    ) -> HumanQuestion:
        human_question = HumanQuestion(
            bot_id=bot_id,
            conversation_id=conversation_id,
            end_user_id=end_user_id,
            lead_id=lead_id,
            question_text=question_text,
            reason=reason,
            status=status,
        )
        session.add(human_question)
        await session.flush()
        return human_question
