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
- `GET /api/v1/telegram/webhook-info`

## Telegram modes

- `TELEGRAM_MODE=polling` (recommended for quick start): bot reads updates via `getUpdates`.
- `TELEGRAM_MODE=webhook`: use Telegram webhook (requires valid HTTPS URL).

## Set webhook (if using webhook mode)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/telegram/set-webhook -H "x-admin-token: <ADMIN_API_TOKEN>"
```
