from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AISM Backend"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    database_url: str = "postgresql+psycopg://aism_app:aism_pass@127.0.0.1:5432/aism_db"

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_webhook_url: str = ""
    admin_api_token: str = ""

    openrouter_api_key: str = ""
    openrouter_model: str = "deepseek/deepseek-v4-flash:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_name: str = "AISM Bot"
    openrouter_app_url: str = "https://openrouter.ai"
    openrouter_temperature: float = 0.3

    bot_reply_max_chars: int = 3900

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
