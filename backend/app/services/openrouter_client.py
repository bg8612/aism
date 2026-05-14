from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings


class OpenRouterClient:
    def __init__(self) -> None:
        self._base_url = settings.openrouter_base_url.rstrip("/")

    async def generate_reply(self, user_text: str) -> str:
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.openrouter_app_url,
            "X-Title": settings.openrouter_app_name,
        }
        payload: dict[str, Any] = {
            "model": settings.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful Telegram bot assistant. Keep answers concise and practical.",
                },
                {"role": "user", "content": user_text},
            ],
            "temperature": settings.openrouter_temperature,
        }

        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(f"{self._base_url}/chat/completions", headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:500]
                raise RuntimeError(f"OpenRouter error {exc.response.status_code}: {body}") from exc
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            return "Could not get a valid model response."

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
            if text_parts:
                return "\n".join(text_parts)

        return "Model returned an empty response."
