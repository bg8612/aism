from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_token
from app.db.session import get_db_session
from app.models.bot import Bot
from app.models.bot_field import BotField
from app.models.bot_question import BotQuestion
from app.models.knowledge_block import KnowledgeBlock
from app.repositories.bot_channel_repository import BotChannelRepository
from app.repositories.bot_field_repository import BotFieldRepository
from app.repositories.bot_question_repository import BotQuestionRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.bot_settings_repository import BotSettingsRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.human_question_repository import HumanQuestionRepository
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.lead_repository import LeadRepository
from app.schemas.bot_admin import BotCreate, BotRead, BotUpdate
from app.schemas.bot_field_admin import BotFieldCreate, BotFieldRead, BotFieldUpdate
from app.schemas.bot_question_admin import BotQuestionCreate, BotQuestionRead, BotQuestionUpdate
from app.schemas.bot_settings_admin import BotSettingsRead, BotSettingsUpdate
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.schemas.human_question_admin import HumanQuestionRead
from app.schemas.knowledge_admin import KnowledgeBlockCreate, KnowledgeBlockRead, KnowledgeBlockUpdate
from app.schemas.lead_admin import LeadRead
from app.services.token_crypto_service import TokenCryptoService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_token)])

client_repo = ClientRepository()
bot_repo = BotRepository()
bot_settings_repo = BotSettingsRepository()
knowledge_repo = KnowledgeRepository()
bot_field_repo = BotFieldRepository()
bot_question_repo = BotQuestionRepository()
lead_repo = LeadRepository()
human_question_repo = HumanQuestionRepository()
bot_channel_repo = BotChannelRepository()
token_crypto = TokenCryptoService()


def _bot_to_schema(bot: Bot, has_token: bool = False, channel_username: str | None = None) -> BotRead:
    return BotRead(
        id=bot.id,
        client_id=bot.client_id,
        name=bot.name,
        telegram_bot_username=bot.telegram_bot_username,
        is_active=bot.is_active,
        created_at=bot.created_at,
        updated_at=bot.updated_at,
        has_token=has_token,
        channel_username=channel_username,
    )


async def _bot_or_404(session: AsyncSession, bot_id: int) -> Bot:
    bot = await bot_repo.get_by_id(session, bot_id=bot_id)
    if bot is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    return bot


async def _field_or_404(session: AsyncSession, field_id: int) -> BotField:
    field = await bot_field_repo.get_by_id(session, field_id=field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    return field


async def _question_or_404(session: AsyncSession, question_id: int) -> BotQuestion:
    question = await bot_question_repo.get_by_id(session, question_id=question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


async def _knowledge_or_404(session: AsyncSession, block_id: int) -> KnowledgeBlock:
    block = await knowledge_repo.get_by_id(session, block_id=block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Knowledge block not found")
    return block


@router.get("/clients", response_model=list[ClientRead])
async def list_clients(session: AsyncSession = Depends(get_db_session)) -> list[ClientRead]:
    return [ClientRead.model_validate(item) for item in await client_repo.list_clients(session)]


@router.post("/clients", response_model=ClientRead)
async def create_client(payload: ClientCreate, session: AsyncSession = Depends(get_db_session)) -> ClientRead:
    client = await client_repo.create_client(
        session,
        name=payload.name,
        contact_name=payload.contact_name,
        contact_phone=payload.contact_phone,
        contact_email=payload.contact_email,
        is_active=payload.is_active,
    )
    await session.commit()
    return ClientRead.model_validate(client)


@router.get("/clients/{client_id}", response_model=ClientRead)
async def get_client(client_id: int, session: AsyncSession = Depends(get_db_session)) -> ClientRead:
    client = await client_repo.get_client(session, client_id=client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return ClientRead.model_validate(client)


@router.patch("/clients/{client_id}", response_model=ClientRead)
async def patch_client(client_id: int, payload: ClientUpdate, session: AsyncSession = Depends(get_db_session)) -> ClientRead:
    client = await client_repo.get_client(session, client_id=client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    await client_repo.update_client(session, client=client, **payload.model_dump(exclude_unset=True))
    await session.commit()
    return ClientRead.model_validate(client)


@router.get("/bots", response_model=list[BotRead])
async def list_bots(session: AsyncSession = Depends(get_db_session)) -> list[BotRead]:
    bots = await bot_repo.list_bots(session)
    result: list[BotRead] = []
    for bot in bots:
        channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot.id, channel_type="telegram")
        result.append(
            _bot_to_schema(
                bot,
                has_token=bool(channel and channel.is_active and channel.bot_token_encrypted),
                channel_username=channel.bot_username if channel else None,
            )
        )
    return result


@router.post("/bots", response_model=BotRead)
async def create_bot(payload: BotCreate, session: AsyncSession = Depends(get_db_session)) -> BotRead:
    bot = await bot_repo.create_bot(
        session,
        name=payload.name,
        telegram_bot_username=payload.telegram_username,
        client_id=payload.client_id,
        is_active=True,
    )
    has_token = False
    if payload.telegram_token:
        await bot_channel_repo.create_or_update_channel(
            session,
            bot_id=bot.id,
            channel_type="telegram",
            bot_token_encrypted=token_crypto.encrypt(payload.telegram_token),
            bot_username=payload.telegram_username,
            webhook_secret=None,
            is_active=True,
        )
        has_token = True
    await session.commit()
    return _bot_to_schema(bot, has_token=has_token, channel_username=payload.telegram_username)


@router.get("/bots/{bot_id}", response_model=BotRead)
async def get_bot(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> BotRead:
    bot = await _bot_or_404(session, bot_id)
    channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot.id, channel_type="telegram")
    return _bot_to_schema(
        bot,
        has_token=bool(channel and channel.is_active and channel.bot_token_encrypted),
        channel_username=channel.bot_username if channel else None,
    )


@router.patch("/bots/{bot_id}", response_model=BotRead)
async def patch_bot(bot_id: int, payload: BotUpdate, session: AsyncSession = Depends(get_db_session)) -> BotRead:
    bot = await _bot_or_404(session, bot_id)
    changes = payload.model_dump(exclude_unset=True, exclude={"telegram_token", "telegram_username"})
    if "client_id" in changes and payload.client_id is None:
        bot.client_id = None
        del changes["client_id"]
    await bot_repo.update_bot(session, bot=bot, telegram_bot_username=payload.telegram_username, **changes)

    channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot.id, channel_type="telegram")
    if payload.telegram_token is not None:
        channel = await bot_channel_repo.create_or_update_channel(
            session,
            bot_id=bot.id,
            channel_type="telegram",
            bot_token_encrypted=token_crypto.encrypt(payload.telegram_token),
            bot_username=payload.telegram_username if payload.telegram_username is not None else (channel.bot_username if channel else None),
            webhook_secret=channel.webhook_secret if channel else None,
            is_active=True,
        )
    elif payload.telegram_username is not None and channel is not None:
        channel.bot_username = payload.telegram_username

    await session.commit()
    if channel is None:
        channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot.id, channel_type="telegram")
    return _bot_to_schema(
        bot,
        has_token=bool(channel and channel.is_active and channel.bot_token_encrypted),
        channel_username=channel.bot_username if channel else None,
    )


@router.post("/bots/{bot_id}/activate", response_model=BotRead)
async def activate_bot(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> BotRead:
    bot = await _bot_or_404(session, bot_id)
    await bot_repo.update_bot(session, bot=bot, is_active=True)
    await session.commit()
    channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot.id, channel_type="telegram")
    return _bot_to_schema(bot, has_token=bool(channel and channel.bot_token_encrypted), channel_username=channel.bot_username if channel else None)


@router.post("/bots/{bot_id}/deactivate", response_model=BotRead)
async def deactivate_bot(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> BotRead:
    bot = await _bot_or_404(session, bot_id)
    await bot_repo.update_bot(session, bot=bot, is_active=False)
    await session.commit()
    channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot.id, channel_type="telegram")
    return _bot_to_schema(bot, has_token=bool(channel and channel.bot_token_encrypted), channel_username=channel.bot_username if channel else None)


@router.get("/bots/{bot_id}/settings", response_model=BotSettingsRead)
async def get_bot_settings(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> BotSettingsRead:
    bot = await _bot_or_404(session, bot_id)
    settings_obj = await bot_settings_repo.get_or_create_by_bot_id(session, bot_id=bot.id, business_name=bot.name)
    await session.commit()
    return BotSettingsRead.model_validate(settings_obj)


@router.patch("/bots/{bot_id}/settings", response_model=BotSettingsRead)
async def patch_bot_settings(
    bot_id: int,
    payload: BotSettingsUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> BotSettingsRead:
    bot = await _bot_or_404(session, bot_id)
    settings_obj = await bot_settings_repo.get_or_create_by_bot_id(session, bot_id=bot.id, business_name=bot.name)
    await bot_settings_repo.update_settings(session, settings_obj=settings_obj, **payload.model_dump(exclude_unset=True))
    await session.commit()
    return BotSettingsRead.model_validate(settings_obj)


@router.get("/bots/{bot_id}/knowledge", response_model=list[KnowledgeBlockRead])
async def list_knowledge(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> list[KnowledgeBlockRead]:
    await _bot_or_404(session, bot_id)
    return [KnowledgeBlockRead.model_validate(item) for item in await knowledge_repo.list_by_bot_id(session, bot_id=bot_id)]


@router.post("/bots/{bot_id}/knowledge", response_model=KnowledgeBlockRead)
async def create_knowledge(
    bot_id: int,
    payload: KnowledgeBlockCreate,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeBlockRead:
    await _bot_or_404(session, bot_id)
    block = await knowledge_repo.create(session, bot_id=bot_id, **payload.model_dump())
    await session.commit()
    return KnowledgeBlockRead.model_validate(block)


@router.patch("/knowledge/{block_id}", response_model=KnowledgeBlockRead)
async def patch_knowledge(
    block_id: int,
    payload: KnowledgeBlockUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeBlockRead:
    block = await _knowledge_or_404(session, block_id)
    await knowledge_repo.update(session, block=block, **payload.model_dump(exclude_unset=True))
    await session.commit()
    return KnowledgeBlockRead.model_validate(block)


@router.delete("/knowledge/{block_id}", response_model=KnowledgeBlockRead)
async def delete_knowledge(block_id: int, session: AsyncSession = Depends(get_db_session)) -> KnowledgeBlockRead:
    block = await _knowledge_or_404(session, block_id)
    await knowledge_repo.deactivate(session, block=block)
    await session.commit()
    return KnowledgeBlockRead.model_validate(block)


@router.get("/bots/{bot_id}/fields", response_model=list[BotFieldRead])
async def list_fields(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> list[BotFieldRead]:
    await _bot_or_404(session, bot_id)
    return [BotFieldRead.model_validate(item) for item in await bot_field_repo.list_by_bot_id(session, bot_id=bot_id)]


@router.post("/bots/{bot_id}/fields", response_model=BotFieldRead)
async def create_field(bot_id: int, payload: BotFieldCreate, session: AsyncSession = Depends(get_db_session)) -> BotFieldRead:
    await _bot_or_404(session, bot_id)
    field = await bot_field_repo.create(session, bot_id=bot_id, **payload.model_dump())
    await session.commit()
    return BotFieldRead.model_validate(field)


@router.patch("/fields/{field_id}", response_model=BotFieldRead)
async def patch_field(field_id: int, payload: BotFieldUpdate, session: AsyncSession = Depends(get_db_session)) -> BotFieldRead:
    field = await _field_or_404(session, field_id)
    await bot_field_repo.update(session, field=field, **payload.model_dump(exclude_unset=True))
    await session.commit()
    return BotFieldRead.model_validate(field)


@router.delete("/fields/{field_id}", response_model=BotFieldRead)
async def delete_field(field_id: int, session: AsyncSession = Depends(get_db_session)) -> BotFieldRead:
    field = await _field_or_404(session, field_id)
    await bot_field_repo.deactivate(session, field=field)
    await session.commit()
    return BotFieldRead.model_validate(field)


@router.get("/bots/{bot_id}/questions", response_model=list[BotQuestionRead])
async def list_questions(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> list[BotQuestionRead]:
    await _bot_or_404(session, bot_id)
    return [BotQuestionRead.model_validate(item) for item in await bot_question_repo.list_by_bot_id(session, bot_id=bot_id)]


@router.post("/bots/{bot_id}/questions", response_model=BotQuestionRead)
async def create_question(
    bot_id: int,
    payload: BotQuestionCreate,
    session: AsyncSession = Depends(get_db_session),
) -> BotQuestionRead:
    await _bot_or_404(session, bot_id)
    field = await _field_or_404(session, payload.field_id)
    if field.bot_id != bot_id:
        raise HTTPException(status_code=400, detail="field_id does not belong to this bot")
    question = await bot_question_repo.create(session, bot_id=bot_id, **payload.model_dump())
    await session.commit()
    return BotQuestionRead.model_validate(question)


@router.patch("/questions/{question_id}", response_model=BotQuestionRead)
async def patch_question(
    question_id: int,
    payload: BotQuestionUpdate,
    session: AsyncSession = Depends(get_db_session),
) -> BotQuestionRead:
    question = await _question_or_404(session, question_id)
    if payload.field_id is not None:
        field = await _field_or_404(session, payload.field_id)
        if field.bot_id != question.bot_id:
            raise HTTPException(status_code=400, detail="field_id does not belong to this bot")
    await bot_question_repo.update(session, question=question, **payload.model_dump(exclude_unset=True))
    await session.commit()
    return BotQuestionRead.model_validate(question)


@router.delete("/questions/{question_id}", response_model=BotQuestionRead)
async def delete_question(question_id: int, session: AsyncSession = Depends(get_db_session)) -> BotQuestionRead:
    question = await _question_or_404(session, question_id)
    await bot_question_repo.deactivate(session, question=question)
    await session.commit()
    return BotQuestionRead.model_validate(question)


@router.get("/bots/{bot_id}/leads", response_model=list[LeadRead])
async def list_leads(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> list[LeadRead]:
    await _bot_or_404(session, bot_id)
    return [LeadRead.model_validate(item) for item in await lead_repo.list_by_bot_id(session, bot_id=bot_id)]


@router.get("/bots/{bot_id}/human-questions", response_model=list[HumanQuestionRead])
async def list_human_questions(bot_id: int, session: AsyncSession = Depends(get_db_session)) -> list[HumanQuestionRead]:
    await _bot_or_404(session, bot_id)
    return [
        HumanQuestionRead.model_validate(item) for item in await human_question_repo.list_by_bot_id(session, bot_id=bot_id)
    ]
