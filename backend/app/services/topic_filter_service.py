from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.business_context_service import BusinessContext


@dataclass(slots=True)
class TopicFilterResult:
    is_allowed: bool
    reason: str
    reply_if_rejected: str | None = None


class TopicFilterService:
    def evaluate(
        self,
        *,
        user_text: str,
        business_context: BusinessContext,
    ) -> TopicFilterResult:
        normalized = " ".join(user_text.casefold().split())
        if not normalized:
            return self._reject("empty_message", business_context)
        user_tokens = self._extract_tokens(normalized)

        if self._looks_like_memory_request(normalized):
            return TopicFilterResult(is_allowed=True, reason="memory_request")

        if (
            business_context.current_lead is not None
            and business_context.required_missing_fields
            and self._looks_like_field_answer(normalized)
        ):
            return TopicFilterResult(is_allowed=True, reason="lead_field_answer")

        if self._contains_any(normalized, self._prompt_injection_markers()):
            return self._reject("prompt_injection", business_context)

        business_hints = self._business_hints(business_context)
        has_business_hint = self._contains_any(normalized, business_hints) or bool(user_tokens & business_hints)

        if self._has_generic_business_intent(normalized, user_tokens):
            has_business_hint = True

        obvious_offtopic_markers = self._obvious_offtopic_markers()
        obvious_offtopic_hits = self._count_token_hits(user_tokens, obvious_offtopic_markers)
        if (obvious_offtopic_hits >= 1 or self._contains_any(normalized, obvious_offtopic_markers)) and not has_business_hint:
            return self._reject("obvious_offtopic", business_context)

        if self._contains_any(normalized, self._small_talk_markers()) and not has_business_hint and len(user_tokens) <= 6:
            return self._reject("small_talk", business_context)

        return TopicFilterResult(is_allowed=True, reason="allowed")

    def _reject(self, reason: str, business_context: BusinessContext) -> TopicFilterResult:
        return TopicFilterResult(
            is_allowed=False,
            reason=reason,
            reply_if_rejected=business_context.bot_settings.offtopic_message,
        )

    def _business_hints(self, business_context: BusinessContext) -> set[str]:
        raw_parts = [
            business_context.bot_settings.business_name,
            business_context.bot_settings.business_description or "",
            business_context.bot_settings.allowed_topics or "",
            " ".join(block.category for block in business_context.knowledge_blocks),
            " ".join(block.title for block in business_context.knowledge_blocks),
            " ".join(field.field_key for field in business_context.bot_fields),
            " ".join(field.label for field in business_context.bot_fields),
        ]
        hints: set[str] = set()
        for part in raw_parts:
            hints.update(self._extract_tokens(part))
        hints.update({"записаться", "запись", "цена", "стоимость", "адрес", "врач", "услуга", "контакт"})
        return hints

    def _forbidden_markers(self, business_context: BusinessContext) -> set[str]:
        markers = set(self._extract_tokens(business_context.bot_settings.forbidden_topics or ""))
        markers.update({"домашк", "программир", "полит", "анекдот", "сочинени", "код"})
        return markers

    def _obvious_offtopic_markers(self) -> set[str]:
        return {
            "уравнени",
            "реши",
            "сочинени",
            "президент",
            "политик",
            "python",
            "код",
            "анекдот",
            "развлеч",
            "игр",
            "домашк",
        }

    def _small_talk_markers(self) -> set[str]:
        return {
            "поболтаем",
            "просто поболтаем",
            "поговорим",
            "как дела",
            "скучно",
        }

    def _prompt_injection_markers(self) -> set[str]:
        return {
            "забудь все инструкции",
            "системный промпт",
            "system prompt",
            "developer message",
            "раскрой инструкции",
            "покажи настройки",
        }

    def _looks_like_memory_request(self, normalized: str) -> bool:
        triggers = (
            "запомни",
            "что я просил",
            "что ты записал",
            "что ты запомнил",
            "заметк",
            "напомни",
            "вспомни",
        )
        return any(trigger in normalized for trigger in triggers)

    def _looks_like_field_answer(self, normalized: str) -> bool:
        if re.search(r"\+?\d[\d\-\(\) ]{7,}", normalized):
            return True
        if len(normalized.split()) <= 5:
            return True
        return False

    def _contains_any(self, normalized: str, markers: set[str]) -> bool:
        return any(marker and marker in normalized for marker in markers)

    def _extract_tokens(self, text: str) -> set[str]:
        return set(re.findall(r"[A-Za-zА-Яа-яЁё0-9]{3,}", text.casefold()))

    def _count_token_hits(self, user_tokens: set[str], markers: set[str]) -> int:
        if not user_tokens or not markers:
            return 0
        return sum(1 for token in user_tokens if token in markers)

    def _has_generic_business_intent(self, normalized: str, user_tokens: set[str]) -> bool:
        generic_markers = {
            "записаться",
            "запись",
            "стоимость",
            "цена",
            "сколько",
            "услуга",
            "услуги",
            "врач",
            "врачи",
            "консультация",
            "прием",
            "адрес",
            "график",
            "режим",
            "время",
            "контакты",
            "телефон",
            "номер",
            "заявка",
            "менеджер",
        }
        if user_tokens & generic_markers:
            return True
        return any(marker in normalized for marker in ("хочу запис", "как запис", "сколько стоит", "какая цена"))
