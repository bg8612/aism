# AISM Backend

## Start local dev

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Database and migrations

```bash
cd backend
.venv\Scripts\activate
alembic upgrade head
```

## Endpoints

- `GET /api/v1/health`
- `POST /api/v1/telegram/webhook`
- `POST /api/v1/telegram/set-webhook`
- `GET /api/v1/telegram/webhook-info`

## Telegram modes

- `TELEGRAM_MODE=polling` (recommended for quick start): bot reads updates via `getUpdates`.
- `TELEGRAM_MODE=webhook`: use Telegram webhook (requires valid HTTPS URL).

## Bot language behavior

- By default, the bot is forced to answer in Russian and keeps replies short.
- You can override this via `OPENROUTER_SYSTEM_PROMPT` in `.env`.

## Message storage flow

- Incoming Telegram message is stored in PostgreSQL (`messages.sender_type = "user"`).
- Bot answer from OpenRouter is stored in PostgreSQL (`messages.sender_type = "bot"`).
- Bot/EndUser/Conversation are created automatically on first message.
- Before requesting OpenRouter, the backend loads a short recent dialogue window and separate passive memory notes from the same chat.

## Set webhook (if using webhook mode)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/telegram/set-webhook -H "x-admin-token: <ADMIN_API_TOKEN>"
```
