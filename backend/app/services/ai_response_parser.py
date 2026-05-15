from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


ALLOWED_INTENTS = {
    "question",
    "lead_request",
    "appointment_request",
    "provide_contact",
    "offtopic",
    "needs_human",
    "other",
}
ALLOWED_LEAD_ACTIONS = {"none", "create", "update", "complete"}


@dataclass(slots=True)
class AIManagerResult:
    reply: str
    intent: str = "other"
    is_on_topic: bool = True
    lead_action: str = "none"
    lead_fields: dict[str, str | None] = field(default_factory=dict)
    needs_human: bool = False
    human_question_reason: str | None = None
    confidence: float = 0.0
    next_question: str | None = None


class AIResponseParser:
    def parse_manager_response(
        self,
        raw_text: str,
        *,
        fallback_reply: str,
    ) -> AIManagerResult:
        payload = self._load_json(raw_text)
        if payload is None:
            return AIManagerResult(reply=self._fallback_or_plain_reply(raw_text, fallback_reply))

        reply = self._coerce_text(payload.get("reply")) or fallback_reply
        intent = self._normalize_choice(payload.get("intent"), ALLOWED_INTENTS, default="other")
        lead_action = self._normalize_choice(payload.get("lead_action"), ALLOWED_LEAD_ACTIONS, default="none")
        lead_fields = self._normalize_lead_fields(payload.get("lead_fields"))
        confidence = self._normalize_confidence(payload.get("confidence"))

        return AIManagerResult(
            reply=reply,
            intent=intent,
            is_on_topic=bool(payload.get("is_on_topic", True)),
            lead_action=lead_action,
            lead_fields=lead_fields,
            needs_human=bool(payload.get("needs_human", False)),
            human_question_reason=self._coerce_text(payload.get("human_question_reason")),
            confidence=confidence,
            next_question=self._coerce_text(payload.get("next_question")),
        )

    def _load_json(self, raw_text: str) -> dict[str, Any] | None:
        stripped = raw_text.strip()
        if not stripped:
            return None

        for candidate in (stripped, self._extract_json_fragment(stripped)):
            if not candidate:
                continue
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
        return None

    def _extract_json_fragment(self, raw_text: str) -> str | None:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        return raw_text[start : end + 1]

    def _normalize_lead_fields(self, value: Any) -> dict[str, str | None]:
        if not isinstance(value, dict):
            return {}

        normalized: dict[str, str | None] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            normalized[key] = self._coerce_text(item)
        return normalized

    def _normalize_choice(self, value: Any, allowed: set[str], *, default: str) -> str:
        if not isinstance(value, str):
            return default
        normalized = value.strip()
        if normalized in allowed:
            return normalized
        return default

    def _normalize_confidence(self, value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, confidence))

    def _coerce_text(self, value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            return text or None
        return str(value).strip() or None

    def _fallback_or_plain_reply(self, raw_text: str, fallback_reply: str) -> str:
        cleaned = re.sub(r"\s+", " ", raw_text).strip()
        if not cleaned:
            return fallback_reply

        # Model sometimes returns plain text instead of JSON; keep user-facing content
        # if it looks like a normal Russian answer.
        has_letters = bool(re.search(r"[A-Za-zА-Яа-яЁё]", cleaned))
        if has_letters and len(cleaned) >= 8:
            return cleaned[:2000]
        return fallback_reply
