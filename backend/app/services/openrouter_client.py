from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.config import settings


EMPTY_REPLY_FALLBACK = (
    "\u0421\u0435\u0439\u0447\u0430\u0441 \u043d\u0435 \u043f\u043e\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c "
    "\u0441\u0444\u043e\u0440\u043c\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043e\u0442\u0432\u0435\u0442. "
    "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0435 \u0440\u0430\u0437."
)

INVALID_REPLY_FALLBACK = (
    "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u043e\u043b\u0443\u0447\u0438\u0442\u044c "
    "\u043a\u043e\u0440\u0440\u0435\u043a\u0442\u043d\u044b\u0439 \u043e\u0442\u0432\u0435\u0442. "
    "\u0421\u0444\u043e\u0440\u043c\u0443\u043b\u0438\u0440\u0443\u0439\u0442\u0435 \u0432\u043e\u043f\u0440\u043e\u0441 "
    "\u0435\u0449\u0435 \u0440\u0430\u0437, \u0438 \u044f \u043e\u0442\u0432\u0435\u0447\u0443 \u043f\u043e-\u0440\u0443\u0441\u0441\u043a\u0438."
)

INTERNAL_RULE_LEAK_FALLBACK = (
    "\u042f \u0442\u0435\u043a\u0441\u0442\u043e\u0432\u044b\u0439 \u0430\u0441\u0441\u0438\u0441\u0442\u0435\u043d\u0442 "
    "\u0432 \u044d\u0442\u043e\u043c \u0431\u043e\u0442\u0435. "
    "\u041f\u043e\u043c\u043e\u0433\u0430\u044e \u0441 \u0432\u043e\u043f\u0440\u043e\u0441\u0430\u043c\u0438 "
    "\u0438 \u0437\u0430\u043c\u0435\u0442\u043a\u0430\u043c\u0438 \u0432\u043d\u0443\u0442\u0440\u0438 \u044d\u0442\u043e\u0433\u043e \u0447\u0430\u0442\u0430."
)

MEMORY_SYSTEM_NOTE = (
    "\u041f\u0430\u0441\u0441\u0438\u0432\u043d\u0430\u044f \u043f\u0430\u043c\u044f\u0442\u044c \u0438\u0437 "
    "\u044d\u0442\u043e\u0433\u043e \u0447\u0430\u0442\u0430. "
    "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439 \u0435\u0435 \u0442\u043e\u043b\u044c\u043a\u043e "
    "\u0435\u0441\u043b\u0438 \u044d\u0442\u043e \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u044c\u043d\u043e "
    "\u043d\u0443\u0436\u043d\u043e \u0434\u043b\u044f \u0442\u0435\u043a\u0443\u0449\u0435\u0433\u043e \u043e\u0442\u0432\u0435\u0442\u0430 "
    "\u0438\u043b\u0438 \u0435\u0441\u043b\u0438 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c "
    "\u043f\u0440\u044f\u043c\u043e \u0441\u043f\u0440\u0430\u0448\u0438\u0432\u0430\u0435\u0442, "
    "\u0447\u0442\u043e \u0442\u044b \u043f\u043e\u043c\u043d\u0438\u0448\u044c."
)

CYRILLIC_PATTERN = re.compile(r"[\u0400-\u04FF]")


class OpenRouterClient:
    def __init__(self) -> None:
        self._base_url = settings.openrouter_base_url.rstrip("/")

    async def generate_reply(
        self,
        user_text: str,
        conversation_messages: list[dict[str, str]] | None = None,
        memory_notes: list[str] | None = None,
    ) -> str:
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.openrouter_app_url,
            "X-Title": settings.openrouter_app_name,
        }
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": settings.openrouter_system_prompt,
            }
        ]
        if memory_notes:
            memory_lines = "\n".join(f"- {note}" for note in memory_notes)
            messages.append(
                {
                    "role": "system",
                    "content": f"{MEMORY_SYSTEM_NOTE}\n{memory_lines}",
                }
            )
        if conversation_messages:
            messages.extend(conversation_messages)
        else:
            messages.append({"role": "user", "content": user_text})

        payload: dict[str, Any] = {
            "model": settings.openrouter_model,
            "messages": messages,
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
            return EMPTY_REPLY_FALLBACK

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

        return EMPTY_REPLY_FALLBACK

    def _sanitize_reply(self, text: str) -> str:
        cleaned = re.sub(r"<[^>\n]{1,80}>", " ", text)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()

        if not cleaned:
            return EMPTY_REPLY_FALLBACK

        if self._looks_like_internal_rule_leak(cleaned):
            return INTERNAL_RULE_LEAK_FALLBACK

        noise_symbols = sum(1 for char in cleaned if char in "{}[]<>#_*`|~^")
        has_cyrillic = bool(CYRILLIC_PATTERN.search(cleaned))
        is_too_noisy = noise_symbols > 12 or (noise_symbols / max(len(cleaned), 1)) > 0.08

        if is_too_noisy or not has_cyrillic:
            return INVALID_REPLY_FALLBACK

        return cleaned

    def _looks_like_internal_rule_leak(self, text: str) -> bool:
        lowered = text.casefold()
        markers = [
            "\u0441\u0438\u0441\u0442\u0435\u043c\u043d",
            "\u043f\u0440\u043e\u043c\u043f\u0442",
            "\u0438\u043d\u0441\u0442\u0440\u0443\u043a\u0446",
            "\u0432\u043d\u0443\u0442\u0440\u0435\u043d",
            "\u0441\u043a\u0440\u044b\u0442",
            "\u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a",
            "\u043a\u043e\u043d\u0444\u0438\u0433\u0443\u0440\u0430\u0446",
            "developer",
            "system message",
            "\u0441\u043b\u0443\u0436\u0435\u0431\u043d",
            "xml/json",
        ]
        return any(marker in lowered for marker in markers)
