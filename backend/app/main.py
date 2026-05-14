from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router as api_router
from app.core.config import settings
from app.services.openrouter_client import OpenRouterClient
from app.services.telegram_client import TelegramClient
from app.services.telegram_polling_runner import TelegramPollingRunner


telegram_runner: TelegramPollingRunner | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global telegram_runner

    if settings.telegram_mode.lower() == "polling":
        telegram_runner = TelegramPollingRunner(
            telegram_client=TelegramClient(),
            openrouter_client=OpenRouterClient(),
        )
        await telegram_runner.start()
    try:
        yield
    finally:
        if telegram_runner is not None:
            await telegram_runner.stop()
            telegram_runner = None


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.include_router(api_router)
    return app


app = create_app()
