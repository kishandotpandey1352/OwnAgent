import re

from app.schemas.memory import MemorySuggestion, MemoryType


MEMORY_TRIGGERS = [
    "remember that",
    "remember i",
    "remember my",
    "for future",
    "from now on",
    "always",
    "i prefer",
    "i like",
    "i want you to",
    "use this preference",
    "save this preference",
]

SENSITIVE_PATTERNS = [
    "ssn",
    "social security",
    "password",
    "credit card",
    "bank account",
    "routing number",
    "salary",
    "income",
    "net worth",
    "portfolio",
    "holdings",
    "shares",
    "i own",
    "my debt",
    "my loan",
    "tax id",
    "address",
    "phone number",
]


def _clean_text(text: str) -> str:
    return " ".join(text.strip().split())


def _normalize_key(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "_", normalized)
    normalized = normalized.strip("_")
    return normalized[:80] or "preference"


def _has_memory_trigger(text: str) -> bool:
    lowered = text.lower()
    return any(trigger in lowered for trigger in MEMORY_TRIGGERS)


def _has_sensitive_content(text: str) -> bool:
    lowered = text.lower()
    return any(pattern in lowered for pattern in SENSITIVE_PATTERNS)


def _remove_memory_prefix(text: str) -> str:
    cleaned = _clean_text(text)

    patterns = [
        r"^remember that\s+",
        r"^remember\s+",
        r"^for future answers,?\s+",
        r"^for future,?\s+",
        r"^from now on,?\s+",
        r"^always\s+",
        r"^please remember that\s+",
        r"^can you remember that\s+",
    ]

    result = cleaned

    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE).strip()

    return result


def _classify_memory_type(text: str) -> tuple[MemoryType, str]:
    lowered = text.lower()

    if any(word in lowered for word in ["chart", "graph", "visual", "plot"]):
        return MemoryType.chart_preference, "preferred_chart_style"

    if any(word in lowered for word in ["risk", "conservative", "cautious", "warning"]):
        return MemoryType.risk_tone, "preferred_risk_tone"

    if any(
        word in lowered
        for word in [
            "annual report",
            "bank liquidity",
            "liquidity",
            "revenue growth",
            "margin",
            "cash flow",
            "risk factor",
            "balance sheet",
        ]
    ):
        return MemoryType.domain_focus, "common_analysis_focus"

    if any(
        word in lowered
        for word in ["cheap", "cheapest", "cost", "provider", "model", "fast", "quality"]
    ):
        return MemoryType.provider_preference, "preferred_provider_routing"

    return MemoryType.answer_style, "preferred_response_style"


def detect_memory_suggestion(text: str) -> MemorySuggestion:
    cleaned = _clean_text(text)

    if not cleaned:
        return MemorySuggestion(
            is_memory_request=False,
            reason="No text was provided.",
        )

    if not _has_memory_trigger(cleaned):
        return MemorySuggestion(
            is_memory_request=False,
            reason="No memory preference trigger was detected.",
        )

    if _has_sensitive_content(cleaned):
        return MemorySuggestion(
            is_memory_request=True,
            confidence=0.8,
            requires_confirmation=True,
            blocked=True,
            reason=(
                "This looks like sensitive personal or financial information, "
                "so it should not be saved as long-term preference memory."
            ),
        )

    memory_value = _remove_memory_prefix(cleaned)

    if len(memory_value) > 500:
        memory_value = memory_value[:497].rstrip() + "..."

    memory_type, default_key = _classify_memory_type(memory_value)

    return MemorySuggestion(
        is_memory_request=True,
        memory_type=memory_type,
        memory_key=_normalize_key(default_key),
        memory_value=memory_value,
        confidence=0.75,
        requires_confirmation=True,
        reason="A safe user preference was detected.",
        blocked=False,
    )