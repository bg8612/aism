from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.bot_field import BotField
from app.models.bot_question import BotQuestion
from app.models.knowledge_block import KnowledgeBlock
from app.repositories.bot_repository import BotRepository
from app.repositories.bot_settings_repository import BotSettingsRepository
from app.core.config import settings


DEMO_SETTINGS = {
    "business_name": "Частная клиника МедПлюс",
    "business_description": "Клиника оказывает услуги терапевта, хирурга, дерматолога и УЗИ.",
    "allowed_topics": "услуги клиники, запись на приём, стоимость услуг, врачи, адрес, график работы",
    "forbidden_topics": "домашние задания, программирование, политика, развлечения, личные советы, диагностика, лечение",
    "offtopic_message": "Я могу помочь только по вопросам клиники: услугам, ценам, записи, врачам, адресу и графику работы.",
    "fallback_message": "У меня нет точной информации по этому вопросу. Я могу зафиксировать вопрос для менеджера.",
    "human_transfer_message": "Я зафиксировал ваш вопрос для менеджера. Специалист сможет уточнить информацию.",
    "answer_only_from_knowledge_base": True,
    "collect_leads": True,
}

DEMO_KNOWLEDGE_BLOCKS = [
    {
        "category": "services",
        "title": "Услуги клиники",
        "content": "Клиника оказывает услуги терапевта, хирурга, дерматолога и УЗИ.",
    },
    {
        "category": "prices",
        "title": "Стоимость консультации хирурга",
        "content": "Консультация хирурга стоит 2500 ₽. Запись подтверждается менеджером.",
    },
    {
        "category": "prices",
        "title": "Стоимость консультации терапевта",
        "content": "Консультация терапевта стоит 2000 ₽.",
    },
    {
        "category": "address",
        "title": "Адрес клиники",
        "content": "Клиника находится по адресу: Москва, ул. Примерная, 10.",
    },
    {
        "category": "limitations",
        "title": "Медицинские ограничения",
        "content": (
            "Бот не ставит диагноз, не назначает лечение и не даёт медицинские рекомендации. "
            "По медицинским вопросам бот предлагает записаться к врачу или передать вопрос менеджеру."
        ),
    },
]

DEMO_FIELDS = [
    {"field_key": "name", "label": "Имя", "field_type": "text", "is_required": True, "order_index": 1, "validation_type": "text"},
    {"field_key": "phone", "label": "Телефон", "field_type": "phone", "is_required": True, "order_index": 2, "validation_type": "phone"},
    {"field_key": "service", "label": "Услуга", "field_type": "text", "is_required": True, "order_index": 3, "validation_type": "text"},
    {"field_key": "preferred_time", "label": "Удобное время", "field_type": "text", "is_required": False, "order_index": 4, "validation_type": "text"},
    {"field_key": "comment", "label": "Комментарий", "field_type": "text", "is_required": False, "order_index": 5, "validation_type": "text"},
]

DEMO_QUESTIONS = {
    "name": "Как вас зовут?",
    "phone": "Укажите, пожалуйста, номер телефона для связи.",
    "service": "Какая услуга вас интересует?",
    "preferred_time": "Когда вам было бы удобно прийти?",
    "comment": "Хотите добавить комментарий для менеджера?",
}


async def main() -> None:
    async with AsyncSessionLocal() as session:
        bot_repository = BotRepository()
        bot_settings_repository = BotSettingsRepository()

        bot = await bot_repository.get_or_create_telegram_bot(
            session,
            name=settings.bot_name,
            telegram_bot_username=settings.telegram_bot_username or None,
        )
        bot_settings = await bot_settings_repository.get_or_create_by_bot_id(
            session,
            bot_id=bot.id,
            business_name=DEMO_SETTINGS["business_name"],
        )
        for key, value in DEMO_SETTINGS.items():
            setattr(bot_settings, key, value)

        for block_data in DEMO_KNOWLEDGE_BLOCKS:
            existing_block = await session.scalar(
                select(KnowledgeBlock)
                .where(KnowledgeBlock.bot_id == bot.id)
                .where(KnowledgeBlock.title == block_data["title"])
                .limit(1)
            )
            if existing_block is None:
                existing_block = KnowledgeBlock(bot_id=bot.id, is_active=True, **block_data)
                session.add(existing_block)
            else:
                existing_block.category = block_data["category"]
                existing_block.content = block_data["content"]
                existing_block.is_active = True

        field_map: dict[str, BotField] = {}
        for field_data in DEMO_FIELDS:
            existing_field = await session.scalar(
                select(BotField)
                .where(BotField.bot_id == bot.id)
                .where(BotField.field_key == field_data["field_key"])
                .limit(1)
            )
            if existing_field is None:
                existing_field = BotField(bot_id=bot.id, is_active=True, **field_data)
                session.add(existing_field)
                await session.flush()
            else:
                existing_field.label = field_data["label"]
                existing_field.field_type = field_data["field_type"]
                existing_field.is_required = field_data["is_required"]
                existing_field.order_index = field_data["order_index"]
                existing_field.validation_type = field_data["validation_type"]
                existing_field.is_active = True
            field_map[field_data["field_key"]] = existing_field

        for field_key, question_text in DEMO_QUESTIONS.items():
            field = field_map[field_key]
            existing_question = await session.scalar(
                select(BotQuestion)
                .where(BotQuestion.bot_id == bot.id)
                .where(BotQuestion.field_id == field.id)
                .limit(1)
            )
            if existing_question is None:
                session.add(
                    BotQuestion(
                        bot_id=bot.id,
                        field_id=field.id,
                        question_text=question_text,
                        is_required=field.is_required,
                        order_index=field.order_index,
                        is_active=True,
                    )
                )
            else:
                existing_question.question_text = question_text
                existing_question.is_required = field.is_required
                existing_question.order_index = field.order_index
                existing_question.is_active = True

        await session.commit()
        print(f"Demo clinic data seeded for bot_id={bot.id}")


if __name__ == "__main__":
    asyncio.run(main())
