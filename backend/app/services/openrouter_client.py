from __future__ import annotations

import re
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
                    "content": settings.openrouter_system_prompt,
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
            return "Сейчас не получилось сформировать ответ. Попробуйте еще раз."

        message = choices[0].get("message") or {}
        content = message.get("content")

        if isinstance(content, str) and content.strip():
            return self._sanitize_reply(content)

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text")
                    if isinstance(text, str) and text.strip():
                        text_parts.append(text.strip())
            if text_parts:
                return self._sanitize_reply("\n".join(text_parts))

        return "Сейчас не получилось сформировать ответ. Попробуйте еще раз."

    def _sanitize_reply(self, text: str) -> str:
        cleaned = re.sub(r"<[^>\n]{1,80}>", " ", text)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

        if not cleaned:
            return "Сейчас не получилось сформировать ответ. Попробуйте еще раз."

        noise_symbols = sum(1 for ch in cleaned if ch in "{}[]<>#_*`|~^")
        has_cyrillic = bool(re.search(r"[А-Яа-яЁё]", cleaned))
        is_too_noisy = noise_symbols > 12 or (noise_symbols / max(len(cleaned), 1)) > 0.08

        if is_too_noisy or not has_cyrillic:
            return "Не удалось получить корректный ответ. Сформулируйте вопрос еще раз, и я отвечу по-русски."

        return cleaned
