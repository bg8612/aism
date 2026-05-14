# AISM Backend

## Start local dev

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Endpoints

- `GET /api/v1/health`
- `POST /api/v1/telegram/webhook`
- `POST /api/v1/telegram/set-webhook`

## Telegram flow

1. Telegram sends update to `/api/v1/telegram/webhook`.
2. Backend sends user text to OpenRouter (`deepseek/deepseek-v4-flash:free`).
3. Backend sends model reply back via Telegram `sendMessage`.

## Set webhook

Set `TELEGRAM_WEBHOOK_URL` in `.env` and call:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/telegram/set-webhook -H "x-admin-token: <ADMIN_API_TOKEN>"
```
