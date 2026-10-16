from __future__ import annotations

import re

from dataclasses import dataclass

from app.schemas.web import (
    WebProductResearchSummary,
)


# =========================================================
# Phase 3H-F-F
# Deterministic browser-facing web citation integrity guard
# =========================================================

_WEB_CITATION_TOKEN_PATTERN = re.compile(
    r"\[Web Source\s+([^\]]+)\]",
    re.IGNORECASE,
)


@dataclass(
    frozen=True,
)
class WebCitationGuardResult:
    answer: str

    referenced_source_numbers: tuple[
        int,
        ...,
    ]

    invalid_citations: tuple[
        str,
        ...,
    ]

    changed: bool


def enforce_web_citation_integrity(
    *,
    answer: str,
    web_research: WebProductResearchSummary,
) -> WebCitationGuardResult:
    """
    Ensure every [Web Source N] reference in the final answer
    points to a browser-safe citation that actually exists in
    WebProductResearchSummary.citations.

    This is deliberately deterministic and runs AFTER answer
    generation.

    Valid:
        [Web Source 2001]

    Invalid examples:
        [Web Source 2999]
        [Web Source abc]
        [Web Source 2001x]

    Invalid tokens are replaced with a non-linkable marker so
    the frontend cannot accidentally present a hallucinated
    source number as a real citation.
    """

    clean_answer = str(
        answer
        or ""
    )

    allowed_source_numbers = {
        int(
            citation.source_number
        )
        for citation
        in (
            web_research.citations
            or []
        )
    }

    referenced: list[
        int
    ] = []

    invalid: list[
        str
    ] = []

    def _replace(
        match: re.Match[str],
    ) -> str:
        raw_token = (
            match.group(
                0
            )
        )

        raw_number = (
            match.group(
                1
            )
            .strip()
        )

        try:
            source_number = int(
                raw_number
            )

        except (
            TypeError,
            ValueError,
        ):
            invalid.append(
                raw_token
            )

            return (
                "[Web citation unavailable]"
            )

        referenced.append(
            source_number
        )

        if (
            source_number
            not in allowed_source_numbers
        ):
            invalid.append(
                raw_token
            )

            return (
                "[Web citation unavailable]"
            )

        # Canonicalize the formatting.
        return (
            f"[Web Source "
            f"{source_number}]"
        )

    guarded_answer = (
        _WEB_CITATION_TOKEN_PATTERN
        .sub(
            _replace,
            clean_answer,
        )
    )

    return (
        WebCitationGuardResult(
            answer=(
                guarded_answer
            ),
            referenced_source_numbers=(
                tuple(
                    referenced
                )
            ),
            invalid_citations=(
                tuple(
                    invalid
                )
            ),
            changed=(
                guarded_answer
                != clean_answer
            ),
        )
    )
