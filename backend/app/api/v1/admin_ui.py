from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.repositories.bot_channel_repository import BotChannelRepository
from app.repositories.bot_field_repository import BotFieldRepository
from app.repositories.bot_prompt_repository import BotPromptRepository
from app.repositories.bot_question_repository import BotQuestionRepository
from app.repositories.bot_repository import BotRepository
from app.repositories.bot_settings_repository import BotSettingsRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.human_question_repository import HumanQuestionRepository
from app.repositories.knowledge_repository import KnowledgeRepository
from app.repositories.lead_repository import LeadRepository
from app.repositories.message_repository import MessageRepository
from app.services.telegram_client import TelegramClient
from app.services.token_crypto_service import TokenCryptoService

router = APIRouter(tags=["admin-ui"])
templates = Jinja2Templates(directory="app/admin_ui/templates")

bot_repo = BotRepository()
bot_channel_repo = BotChannelRepository()
bot_settings_repo = BotSettingsRepository()
bot_prompt_repo = BotPromptRepository()
knowledge_repo = KnowledgeRepository()
bot_field_repo = BotFieldRepository()
bot_question_repo = BotQuestionRepository()
lead_repo = LeadRepository()
human_question_repo = HumanQuestionRepository()
conversation_repo = ConversationRepository()
message_repo = MessageRepository()
token_crypto = TokenCryptoService()


def _is_ui_authorized(request: Request) -> bool:
    token = request.cookies.get("admin_token")
    return bool(settings.admin_api_token and token == settings.admin_api_token)


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=302)


async def _session() -> AsyncSession:
    return AsyncSessionLocal()


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/admin/login", response_class=HTMLResponse)
async def admin_login_submit(request: Request, token: str = Form(...)):
    if not settings.admin_api_token or token != settings.admin_api_token:
        return templates.TemplateResponse(request, "login.html", {"error": "Неверный токен"})
    response = RedirectResponse(url="/admin/bots", status_code=302)
    response.set_cookie("admin_token", token, httponly=True, samesite="lax")
    return response


@router.get("/admin", response_class=HTMLResponse)
async def admin_root() -> RedirectResponse:
    return RedirectResponse(url="/admin/bots", status_code=302)


@router.get("/admin/bots", response_class=HTMLResponse)
async def bots_list(request: Request):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bots = await bot_repo.list_bots(session)
        rows = []
        for bot in bots:
            channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot.id, channel_type="telegram")
            rows.append({"bot": bot, "channel": channel})
    return templates.TemplateResponse(request, "bots_list.html", {"rows": rows})


@router.get("/admin/bots/new", response_class=HTMLResponse)
async def bot_new_page(request: Request):
    if not _is_ui_authorized(request):
        return _redirect_login()
    return templates.TemplateResponse(request, "bot_new.html", {})


@router.post("/admin/bots/new")
async def bot_new_submit(
    request: Request,
    name: str = Form(...),
    telegram_username: str = Form(default=""),
    telegram_token: str = Form(default=""),
) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.create_bot(
            session,
            name=name,
            telegram_bot_username=telegram_username.strip() or None,
            client_id=None,
            is_active=True,
        )
        if telegram_token.strip():
            await bot_channel_repo.create_or_update_channel(
                session,
                bot_id=bot.id,
                channel_type="telegram",
                bot_token_encrypted=token_crypto.encrypt(telegram_token.strip()),
                bot_username=telegram_username.strip() or None,
                webhook_secret=None,
                is_active=True,
            )
        await bot_prompt_repo.get_or_create_defaults(session, bot_id=bot.id)
        await session.commit()
        return RedirectResponse(url=f"/admin/bots/{bot.id}", status_code=302)


@router.get("/admin/bots/{bot_id}", response_class=HTMLResponse)
async def bot_edit_page(request: Request, bot_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot_id, channel_type="telegram")
        settings_obj = await bot_settings_repo.get_or_create_by_bot_id(session, bot_id=bot.id, business_name=bot.name)
        await session.commit()
    return templates.TemplateResponse(
        request,
        "bot_edit.html",
        {"bot": bot, "channel": channel, "settings_obj": settings_obj},
    )


@router.post("/admin/bots/{bot_id}")
async def bot_edit_submit(
    request: Request,
    bot_id: int,
    name: str = Form(...),
    is_active: str = Form(default="off"),
    telegram_username: str = Form(default=""),
    telegram_token: str = Form(default=""),
    business_name: str = Form(...),
    business_description: str = Form(default=""),
    allowed_topics: str = Form(default=""),
    forbidden_topics: str = Form(default=""),
    offtopic_message: str = Form(...),
    fallback_message: str = Form(...),
    human_transfer_message: str = Form(...),
    answer_only_from_knowledge_base: str = Form(default="off"),
    collect_leads: str = Form(default="off"),
) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        await bot_repo.update_bot(
            session,
            bot=bot,
            name=name,
            telegram_bot_username=telegram_username.strip() or None,
            is_active=(is_active == "on"),
        )
        channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=bot_id, channel_type="telegram")
        if telegram_token.strip():
            await bot_channel_repo.create_or_update_channel(
                session,
                bot_id=bot_id,
                channel_type="telegram",
                bot_token_encrypted=token_crypto.encrypt(telegram_token.strip()),
                bot_username=telegram_username.strip() or None,
                webhook_secret=channel.webhook_secret if channel else None,
                is_active=True,
            )
        elif channel is not None:
            channel.bot_username = telegram_username.strip() or None

        settings_obj = await bot_settings_repo.get_or_create_by_bot_id(session, bot_id=bot_id, business_name=bot.name)
        await bot_settings_repo.update_settings(
            session,
            settings_obj=settings_obj,
            business_name=business_name,
            business_description=business_description,
            allowed_topics=allowed_topics,
            forbidden_topics=forbidden_topics,
            offtopic_message=offtopic_message,
            fallback_message=fallback_message,
            human_transfer_message=human_transfer_message,
            answer_only_from_knowledge_base=(answer_only_from_knowledge_base == "on"),
            collect_leads=(collect_leads == "on"),
        )
        await session.commit()
    return RedirectResponse(url=f"/admin/bots/{bot_id}", status_code=302)


@router.get("/admin/bots/{bot_id}/knowledge", response_class=HTMLResponse)
async def knowledge_page(request: Request, bot_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        items = await knowledge_repo.list_by_bot_id(session, bot_id=bot_id)
    return templates.TemplateResponse(request, "knowledge_edit.html", {"bot": bot, "items": items})


@router.post("/admin/bots/{bot_id}/knowledge")
async def knowledge_create(
    request: Request,
    bot_id: int,
    category: str = Form(...),
    title: str = Form(...),
    content: str = Form(...),
) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        await knowledge_repo.create(session, bot_id=bot_id, category=category, title=title, content=content, is_active=True)
        await session.commit()
    return RedirectResponse(url=f"/admin/bots/{bot_id}/knowledge", status_code=302)


@router.post("/admin/knowledge/{block_id}/disable")
async def knowledge_disable(request: Request, block_id: int) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        block = await knowledge_repo.get_by_id(session, block_id=block_id)
        if block is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        await knowledge_repo.deactivate(session, block=block)
        await session.commit()
        return RedirectResponse(url=f"/admin/bots/{block.bot_id}/knowledge", status_code=302)


@router.get("/admin/bots/{bot_id}/fields", response_class=HTMLResponse)
async def fields_page(request: Request, bot_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        items = await bot_field_repo.list_by_bot_id(session, bot_id=bot_id)
    return templates.TemplateResponse(request, "fields_edit.html", {"bot": bot, "items": items})


@router.post("/admin/bots/{bot_id}/fields")
async def fields_create(
    request: Request,
    bot_id: int,
    field_key: str = Form(...),
    label: str = Form(...),
    field_type: str = Form(default="text"),
    is_required: str = Form(default="off"),
    order_index: int = Form(default=0),
    validation_type: str = Form(default=""),
) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        await bot_field_repo.create(
            session,
            bot_id=bot_id,
            field_key=field_key,
            label=label,
            field_type=field_type,
            is_required=(is_required == "on"),
            order_index=order_index,
            validation_type=validation_type or None,
            is_active=True,
        )
        await session.commit()
    return RedirectResponse(url=f"/admin/bots/{bot_id}/fields", status_code=302)


@router.post("/admin/fields/{field_id}/disable")
async def fields_disable(request: Request, field_id: int) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        field = await bot_field_repo.get_by_id(session, field_id=field_id)
        if field is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        await bot_field_repo.deactivate(session, field=field)
        await session.commit()
        return RedirectResponse(url=f"/admin/bots/{field.bot_id}/fields", status_code=302)


@router.get("/admin/bots/{bot_id}/questions", response_class=HTMLResponse)
async def questions_page(request: Request, bot_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        questions = await bot_question_repo.list_by_bot_id(session, bot_id=bot_id)
        fields = await bot_field_repo.list_by_bot_id(session, bot_id=bot_id)
    return templates.TemplateResponse(
        request,
        "questions_edit.html",
        {"bot": bot, "questions": questions, "fields": fields},
    )


@router.post("/admin/bots/{bot_id}/questions")
async def questions_create(
    request: Request,
    bot_id: int,
    field_id: int = Form(...),
    question_text: str = Form(...),
    is_required: str = Form(default="on"),
    order_index: int = Form(default=0),
) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        await bot_question_repo.create(
            session,
            bot_id=bot_id,
            field_id=field_id,
            question_text=question_text,
            is_required=(is_required == "on"),
            order_index=order_index,
            is_active=True,
        )
        await session.commit()
    return RedirectResponse(url=f"/admin/bots/{bot_id}/questions", status_code=302)


@router.post("/admin/questions/{question_id}/disable")
async def questions_disable(request: Request, question_id: int) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        question = await bot_question_repo.get_by_id(session, question_id=question_id)
        if question is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        await bot_question_repo.deactivate(session, question=question)
        await session.commit()
        return RedirectResponse(url=f"/admin/bots/{question.bot_id}/questions", status_code=302)


@router.get("/admin/bots/{bot_id}/leads", response_class=HTMLResponse)
async def leads_page(request: Request, bot_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        leads = await lead_repo.list_by_bot_id(session, bot_id=bot_id)
    return templates.TemplateResponse(request, "leads_list.html", {"bot": bot, "leads": leads})


@router.get("/admin/bots/{bot_id}/human-questions", response_class=HTMLResponse)
async def human_questions_page(request: Request, bot_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        questions = await human_question_repo.list_by_bot_id(session, bot_id=bot_id)
    return templates.TemplateResponse(request, "human_questions_list.html", {"bot": bot, "questions": questions})


@router.get("/admin/bots/{bot_id}/prompts", response_class=HTMLResponse)
async def prompts_page(request: Request, bot_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        prompts = await bot_prompt_repo.get_or_create_defaults(session, bot_id=bot_id)
        await session.commit()
    return templates.TemplateResponse(request, "prompts_edit.html", {"bot": bot, "prompts": prompts})


@router.post("/admin/prompts/{prompt_id}")
async def prompt_update(
    request: Request,
    prompt_id: int,
    title: str = Form(...),
    content: str = Form(...),
    is_active: str = Form(default="off"),
) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        prompt = await bot_prompt_repo.get_by_id(session, prompt_id=prompt_id)
        if prompt is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        await bot_prompt_repo.update(
            session,
            prompt=prompt,
            title=title,
            content=content,
            is_active=(is_active == "on"),
        )
        await session.commit()
        return RedirectResponse(url=f"/admin/bots/{prompt.bot_id}/prompts", status_code=302)


@router.get("/admin/bots/{bot_id}/conversations", response_class=HTMLResponse)
async def conversations_page(request: Request, bot_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        bot = await bot_repo.get_by_id(session, bot_id=bot_id)
        if bot is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        conversations = await conversation_repo.list_by_bot_id(session, bot_id=bot_id, limit=500)
        leads = await lead_repo.list_by_bot_id(session, bot_id=bot_id)
        human_questions = await human_question_repo.list_by_bot_id(session, bot_id=bot_id)
        lead_ids = {item.conversation_id for item in leads}
        human_ids = {item.conversation_id for item in human_questions}
    return templates.TemplateResponse(
        request,
        "conversations_list.html",
        {"bot": bot, "conversations": conversations, "lead_ids": lead_ids, "human_ids": human_ids},
    )


@router.get("/admin/conversations/{conversation_id}", response_class=HTMLResponse)
async def conversation_detail_page(request: Request, conversation_id: int):
    if not _is_ui_authorized(request):
        return _redirect_login()
    async with await _session() as session:
        conversation = await conversation_repo.get_by_id(session, conversation_id=conversation_id)
        if conversation is None:
            return RedirectResponse(url="/admin/bots", status_code=302)
        messages = await message_repo.list_for_conversation(session, conversation_id=conversation_id, limit=1000)
        bot = await bot_repo.get_by_id(session, bot_id=conversation.bot_id)
    return templates.TemplateResponse(
        request,
        "conversation_detail.html",
        {"conversation": conversation, "messages": messages, "bot": bot},
    )


@router.post("/admin/conversations/{conversation_id}/send-message")
async def conversation_send_message(
    request: Request,
    conversation_id: int,
    text: str = Form(...),
) -> RedirectResponse:
    if not _is_ui_authorized(request):
        return _redirect_login()
    text = text.strip()
    if not text:
        return RedirectResponse(url=f"/admin/conversations/{conversation_id}", status_code=302)

    async with await _session() as session:
        conversation = await conversation_repo.get_by_id(session, conversation_id=conversation_id)
        if conversation is None or conversation.end_user is None:
            return RedirectResponse(url="/admin/bots", status_code=302)

        channel = await bot_channel_repo.get_by_bot_id_and_channel(session, bot_id=conversation.bot_id, channel_type="telegram")
        if channel is not None and channel.is_active and channel.bot_token_encrypted:
            token = token_crypto.decrypt(channel.bot_token_encrypted)
            telegram_client = TelegramClient(bot_token=token)
        else:
            telegram_client = TelegramClient()

        await telegram_client.send_message(chat_id=int(conversation.end_user.external_user_id), text=text)
        await message_repo.create(
            session,
            conversation_id=conversation.id,
            bot_id=conversation.bot_id,
            end_user_id=conversation.end_user_id,
            sender_type="admin",
            message_text=text,
            raw_payload_json={"source": "admin_panel"},
        )
        await session.commit()

    return RedirectResponse(url=f"/admin/conversations/{conversation_id}", status_code=302)
