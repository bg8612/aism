from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import settings

if TYPE_CHECKING:
    from app.models.knowledge_block import KnowledgeBlock
    from app.services.business_context_service import BusinessContext


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
    "Я помогу по вашему запросу и при необходимости уточню детали у коллег."
)

MANAGER_STYLE_FALLBACK = (
    "Давайте подберем лучший вариант под ваш запрос. "
    "Напишите, пожалуйста, бюджет и параметры, а детали по наличию я уточню у коллег."
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

BUSINESS_KNOWLEDGE_NOTE = (
    "\u041d\u0438\u0436\u0435 \u0434\u0430\u043d\u0430 \u0431\u0430\u0437\u0430 \u0437\u043d\u0430\u043d\u0438\u0439 "
    "\u0438 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0431\u0438\u0437\u043d\u0435\u0441\u0430. "
    "\u041e\u043f\u0438\u0440\u0430\u0439\u0441\u044f \u0442\u043e\u043b\u044c\u043a\u043e \u043d\u0430 \u043d\u0438\u0445."
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
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": settings.openrouter_system_prompt,
            }
        ]
        if memory_notes:
            messages.append({"role": "system", "content": self._render_memory_notes(memory_notes)})
        if conversation_messages:
            messages.extend(conversation_messages)
        else:
            messages.append({"role": "user", "content": user_text})

        payload: dict[str, Any] = {
            "model": settings.openrouter_model,
            "messages": messages,
            "temperature": settings.openrouter_temperature,
        }
        data = await self._post_chat_completion(payload)
        content = self._extract_content(data)
        if content is None:
            return EMPTY_REPLY_FALLBACK
        return self._sanitize_reply(content)

    async def generate_business_manager_response(
        self,
        *,
        user_text: str,
        conversation_messages: list[dict[str, str]] | None,
        memory_notes: list[str] | None,
        business_context: BusinessContext,
        knowledge_blocks: list[KnowledgeBlock],
        current_lead_data: dict[str, str] | None,
        missing_required_fields: list[str] | None,
    ) -> str:
        fallback_reply = business_context.bot_settings.fallback_message
        system_prompt = settings.openrouter_business_manager_prompt.replace(
            "{business_name}",
            business_context.bot_settings.business_name,
        )
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": self._render_business_context_note(business_context, knowledge_blocks, current_lead_data, missing_required_fields)},
        ]
        if memory_notes:
            messages.append({"role": "system", "content": self._render_memory_notes(memory_notes)})
        if conversation_messages:
            messages.extend(conversation_messages)
        else:
            messages.append({"role": "user", "content": user_text})

        payload: dict[str, Any] = {
            "model": settings.openrouter_model,
            "messages": messages,
            "temperature": settings.openrouter_temperature,
            "response_format": {"type": "json_object"},
        }
        data = await self._post_chat_completion(payload)
        content = self._extract_content(data)
        if content is None:
            return json.dumps(self._fallback_manager_payload(fallback_reply), ensure_ascii=False)
        return content.strip()

    def sanitize_manager_reply(self, reply: str, *, fallback_message: str) -> str:
        cleaned = re.sub(r"<[^>\n]{1,80}>", " ", reply)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", " ", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        if not cleaned:
            return fallback_message
        if self._looks_like_internal_rule_leak(cleaned):
            return MANAGER_STYLE_FALLBACK
        if self._looks_robotic_or_invalid(cleaned):
            return MANAGER_STYLE_FALLBACK
        return self._polish_common_typos(cleaned)

    async def _post_chat_completion(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": settings.openrouter_app_url,
            "X-Title": settings.openrouter_app_name,
        }
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(f"{self._base_url}/chat/completions", headers=headers, json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                body = exc.response.text[:500]
                raise RuntimeError(f"OpenRouter error {exc.response.status_code}: {body}") from exc
            return response.json()

    def _extract_content(self, data: dict[str, Any]) -> str | None:
        choices = data.get("choices") or []
        if not choices:
            return None

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
        return None

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

    def _render_memory_notes(self, memory_notes: list[str]) -> str:
        memory_lines = "\n".join(f"- {note}" for note in memory_notes)
        return f"{MEMORY_SYSTEM_NOTE}\n{memory_lines}"

    def _render_business_context_note(
        self,
        business_context: BusinessContext,
        knowledge_blocks: list[KnowledgeBlock],
        current_lead_data: dict[str, str] | None,
        missing_required_fields: list[str] | None,
    ) -> str:
        lead_json = json.dumps(current_lead_data or {}, ensure_ascii=False)
        missing_json = json.dumps(missing_required_fields or [], ensure_ascii=False)
        field_lines = []
        for field in business_context.bot_fields:
            field_lines.append(
                f"- key={field.field_key}; label={field.label}; type={field.field_type}; required={field.is_required}; "
                f"validation={field.validation_type or 'none'}"
            )
        question_lines = []
        for question in business_context.bot_questions:
            field_key = question.field.field_key if question.field is not None else "unknown"
            question_lines.append(f"- {field_key}: {question.question_text}")

        knowledge_lines = []
        for block in knowledge_blocks:
            content = block.content.strip()
            if len(content) > settings.openrouter_business_knowledge_chars_per_block:
                content = content[: settings.openrouter_business_knowledge_chars_per_block].rstrip() + "..."
            knowledge_lines.append(f"[{block.category}] {block.title}: {content}")

        return (
            f"{BUSINESS_KNOWLEDGE_NOTE}\n"
            f"business_name: {business_context.bot_settings.business_name}\n"
            f"business_description: {business_context.bot_settings.business_description or ''}\n"
            f"allowed_topics: {business_context.bot_settings.allowed_topics or ''}\n"
            f"forbidden_topics: {business_context.bot_settings.forbidden_topics or ''}\n"
            f"answer_only_from_knowledge_base: {business_context.bot_settings.answer_only_from_knowledge_base}\n"
            f"fallback_message: {business_context.bot_settings.fallback_message}\n"
            f"human_transfer_message: {business_context.bot_settings.human_transfer_message}\n"
            f"current_lead_data: {lead_json}\n"
            f"missing_required_fields: {missing_json}\n"
            f"lead_fields_schema:\n" + ("\n".join(field_lines) if field_lines else "- none") + "\n"
            f"lead_questions:\n" + ("\n".join(question_lines) if question_lines else "- none") + "\n"
            f"knowledge_base:\n" + ("\n".join(knowledge_lines) if knowledge_lines else "- knowledge is empty")
        )

    def _fallback_manager_payload(self, fallback_reply: str) -> dict[str, Any]:
        return {
            "reply": fallback_reply,
            "intent": "other",
            "is_on_topic": True,
            "lead_action": "none",
            "lead_fields": {},
            "needs_human": False,
            "human_question_reason": None,
            "confidence": 0.0,
            "next_question": None,
        }

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

    def _looks_robotic_or_invalid(self, text: str) -> bool:
        lowered = text.casefold().strip()
        robotic_markers = [
            "я бот",
            "я нейросеть",
            "я ии",
            "передам менеджеру",
            "передам ваш вопрос менеджеру",
            "не удалось получить корректный ответ",
            "time",
        ]
        if lowered in {"time", "тайм", "ok", "none"}:
            return True
        if len(lowered) <= 4:
            return True
        return any(marker in lowered for marker in robotic_markers)

    def _polish_common_typos(self, text: str) -> str:
        replacements = {
            r"\bо нашу\b": "о нашей",
            r"\bпо бьенам\b": "по ценам",
            r"\bя можем\b": "мы можем",
            r"\bуенам\b": "ценам",
            r"\bуены\b": "цены",
        }
        cleaned = text
        for pattern, repl in replacements.items():
            cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
        return cleaned
