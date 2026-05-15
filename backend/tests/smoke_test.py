from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
from typing import AsyncGenerator

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.api.v1 import admin_ui
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import create_app
from app.models.bot_settings import BotSettings
from app.services.ai_response_parser import AIResponseParser
from app.services.lead_processing_service import LeadProcessingService
from app.services.topic_filter_service import TopicFilterService


DB_PATH = Path("tests/smoke_test.db")
DB_URL = f"sqlite+aiosqlite:///{DB_PATH.as_posix()}"


def _setup_db() -> async_sessionmaker[AsyncSession]:
    if DB_PATH.exists():
        DB_PATH.unlink()
    engine = create_async_engine(DB_URL, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

    async def create_schema() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_schema())
    return session_factory


def run() -> None:
    session_factory = _setup_db()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db
    admin_ui.AsyncSessionLocal = session_factory  # type: ignore[assignment]

    settings.admin_api_token = "smoke_admin_token"

    client = TestClient(app)

    # Admin auth checks.
    assert client.get("/api/v1/admin/bots").status_code == 401
    assert client.get(
        "/api/v1/admin/bots",
        headers={"Authorization": "Bearer wrong"},
    ).status_code == 401

    headers = {"Authorization": f"Bearer {settings.admin_api_token}"}
    assert client.get("/api/v1/admin/bots", headers=headers).status_code == 200

    # Client + Bot + Settings + Knowledge.
    created_client = client.post(
        "/api/v1/admin/clients",
        headers=headers,
        json={"name": "Clinic A", "is_active": True},
    )
    assert created_client.status_code == 200
    client_id = created_client.json()["id"]

    created_bot = client.post(
        "/api/v1/admin/bots",
        headers=headers,
        json={
            "client_id": client_id,
            "name": "Clinic Bot",
            "telegram_username": "clinic_test_bot",
            "telegram_token": "123:abc",
        },
    )
    assert created_bot.status_code == 200
    bot_payload = created_bot.json()
    bot_id = bot_payload["id"]
    assert bot_payload["has_token"] is True
    assert "telegram_token" not in bot_payload
    assert "bot_token_encrypted" not in bot_payload

    bot_settings = client.get(f"/api/v1/admin/bots/{bot_id}/settings", headers=headers)
    assert bot_settings.status_code == 200

    updated_settings = client.patch(
        f"/api/v1/admin/bots/{bot_id}/settings",
        headers=headers,
        json={
            "business_name": "Клиника А",
            "offtopic_message": "Только по теме клиники.",
        },
    )
    assert updated_settings.status_code == 200
    assert updated_settings.json()["business_name"] == "Клиника А"

    kb_create = client.post(
        f"/api/v1/admin/bots/{bot_id}/knowledge",
        headers=headers,
        json={"category": "prices", "title": "Хирург", "content": "2500 ₽"},
    )
    assert kb_create.status_code == 200
    block_id = kb_create.json()["id"]

    kb_disable = client.delete(f"/api/v1/admin/knowledge/{block_id}", headers=headers)
    assert kb_disable.status_code == 200
    assert kb_disable.json()["is_active"] is False

    # Admin UI auth/login checks.
    ui_no_cookie = client.get("/admin/bots", follow_redirects=False)
    assert ui_no_cookie.status_code in (302, 307)

    ui_login_fail = client.post("/admin/login", data={"token": "bad"})
    assert ui_login_fail.status_code == 200
    assert "Неверный токен" in ui_login_fail.text

    ui_login_ok = client.post("/admin/login", data={"token": settings.admin_api_token}, follow_redirects=False)
    assert ui_login_ok.status_code in (302, 303, 307)

    ui_bots = client.get("/admin/bots")
    assert ui_bots.status_code == 200

    # Service-level smoke.
    parser = AIResponseParser()
    parsed = parser.parse_manager_response("Конечно! {сломанный json", fallback_reply="fallback")
    assert isinstance(parsed.reply, str)
    assert parsed.reply.strip() != ""

    tf = TopicFilterService()
    bs = BotSettings(
        bot_id=1,
        business_name="Клиника А",
        business_description="услуги и запись",
        allowed_topics="услуги, запись, цены",
        forbidden_topics="домашка, политика, программирование",
        offtopic_message="Только по теме",
        fallback_message="fallback",
        human_transfer_message="human",
        answer_only_from_knowledge_base=True,
        collect_leads=True,
    )
    class DummyCtx:
        bot_settings = bs
        current_lead = None
        required_missing_fields = []
        knowledge_blocks = []
        bot_fields = []

    result = tf.evaluate(user_text="реши уравнение 2x+5=10", business_context=DummyCtx())  # type: ignore[arg-type]
    assert result.is_allowed is False

    norm = LeadProcessingService()._normalize_field_value(field_key="phone", raw_value="89991234567")
    assert norm == "+7 999 123-45-67"

    print("SMOKE_TEST_OK")


if __name__ == "__main__":
    os.chdir(ROOT_DIR)
    run()
