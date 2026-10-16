from __future__ import annotations

import re
from typing import Any

from app.core.config import settings

from app.schemas.web import (
    WebGapDecision,
)


YEAR_PATTERN = re.compile(
    r"\b((?:19|20)\d{2})\b"
)


YEAR_RANGE_PATTERN = re.compile(
    (
        r"\b((?:19|20)\d{2})\b"
        r"\s*"
        r"(?:-|–|—|to|through)"
        r"\s*"
        r"\b((?:19|20)\d{2})\b"
    ),
    re.IGNORECASE,
)


CURRENT_SIGNALS = (
    "latest",
    "current",
    "currently",
    "today",
    "right now",
    "most recent",
    "as of today",
    "as of now",
    "this year",
)


def _enum_value(
    value: Any,
) -> str:
    if value is None:
        return ""

    if hasattr(
        value,
        "value",
    ):
        return str(
            value.value
        )

    return str(
        value
    )


def _result_output(
    result: Any,
) -> dict[str, Any]:
    if isinstance(
        result,
        dict,
    ):
        output = result.get(
            "output"
        )

        return (
            output
            if isinstance(
                output,
                dict,
            )
            else {}
        )

    output = getattr(
        result,
        "output",
        None,
    )

    return (
        output
        if isinstance(
            output,
            dict,
        )
        else {}
    )


def _result_tool_name(
    result: Any,
) -> str:
    if isinstance(
        result,
        dict,
    ):
        return _enum_value(
            result.get(
                "tool_name"
            )
        )

    return _enum_value(
        getattr(
            result,
            "tool_name",
            None,
        )
    )


def _result_status(
    result: Any,
) -> str:
    if isinstance(
        result,
        dict,
    ):
        return _enum_value(
            result.get(
                "status"
            )
        )

    return _enum_value(
        getattr(
            result,
            "status",
            None,
        )
    )


def _find_completed_result(
    *,
    tool_results: list[Any],
    tool_name: str,
) -> Any | None:
    for result in tool_results:
        if (
            _result_tool_name(
                result
            )
            != tool_name
        ):
            continue

        if (
            _result_status(
                result
            )
            != "completed"
        ):
            continue

        return result

    return None


def _requested_years(
    question: str,
) -> set[int]:
    years = {
        int(
            value
        )
        for value in (
            YEAR_PATTERN.findall(
                question
            )
        )
    }

    for (
        start_value,
        end_value,
    ) in YEAR_RANGE_PATTERN.findall(
        question
    ):
        start_year = int(
            start_value
        )

        end_year = int(
            end_value
        )

        if (
            end_year
            >= start_year
            and end_year
            - start_year
            <= 10
        ):
            years.update(
                range(
                    start_year,
                    end_year + 1,
                )
            )

    return years


def _fact_years(
    fact: dict[str, Any],
) -> set[int]:
    years: set[int] = set()

    values = (
        fact.get(
            "period_label"
        ),
        fact.get(
            "period_start"
        ),
        fact.get(
            "period_end"
        ),
    )

    for value in values:
        if not value:
            continue

        for match in (
            YEAR_PATTERN.findall(
                str(
                    value
                )
            )
        ):
            years.add(
                int(
                    match
                )
            )

    return years


def _source_score(
    source: dict[str, Any],
) -> float | None:
    value = source.get(
        "score"
    )

    if value is None:
        value = source.get(
            "retrieval_score"
        )

    if value is None:
        return None

    try:
        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


def detect_web_gap(
    *,
    question: str,
    use_documents: bool,
    tool_results: list[Any],
) -> WebGapDecision:
    """
    Decide whether local document evidence appears
    insufficient.

    This function NEVER performs web research.

    It only examines existing local tool results.
    """

    if not use_documents:
        return WebGapDecision(
            needs_web=True,
            reason=(
                "No uploaded-document evidence is "
                "available for this request."
            ),
        )

    requested_years = (
        _requested_years(
            question
        )
    )

    lowered_question = (
        question
        .lower()
        .strip()
    )

    asks_for_current = any(
        signal
        in lowered_question
        for signal
        in CURRENT_SIGNALS
    )

    fact_result = (
        _find_completed_result(
            tool_results=(
                tool_results
            ),
            tool_name=(
                "financial_fact_extractor"
            ),
        )
    )

    if fact_result is not None:
        fact_output = (
            _result_output(
                fact_result
            )
        )

        facts = (
            fact_output.get(
                "facts"
            )
            or []
        )

        facts = [
            fact
            for fact in facts
            if isinstance(
                fact,
                dict,
            )
        ]

        covered_years: set[int] = set()

        for fact in facts:
            covered_years.update(
                _fact_years(
                    fact
                )
            )

        missing_years = (
            requested_years
            - covered_years
        )

        if not facts:
            return WebGapDecision(
                needs_web=True,
                reason=(
                    "The uploaded documents "
                    "did not produce a validated "
                    "financial fact matching "
                    "the requested metric."
                ),
                requested_years=sorted(
                    requested_years
                ),
                covered_years=[],
                missing_years=sorted(
                    requested_years
                ),
                local_fact_count=0,
            )

        if missing_years:
            return WebGapDecision(
                needs_web=True,
                reason=(
                    "Validated document facts "
                    "do not cover all requested "
                    "periods: "
                    + ", ".join(
                        str(
                            year
                        )
                        for year in sorted(
                            missing_years
                        )
                    )
                    + "."
                ),
                requested_years=sorted(
                    requested_years
                ),
                covered_years=sorted(
                    covered_years
                ),
                missing_years=sorted(
                    missing_years
                ),
                local_fact_count=len(
                    facts
                ),
            )

        if asks_for_current:
            return WebGapDecision(
                needs_web=True,
                reason=(
                    "The question asks for "
                    "current or latest "
                    "information that may extend "
                    "beyond the uploaded report."
                ),
                requested_years=sorted(
                    requested_years
                ),
                covered_years=sorted(
                    covered_years
                ),
                local_fact_count=len(
                    facts
                ),
            )

        return WebGapDecision(
            needs_web=False,
            requested_years=sorted(
                requested_years
            ),
            covered_years=sorted(
                covered_years
            ),
            local_fact_count=len(
                facts
            ),
        )

    document_result = (
        _find_completed_result(
            tool_results=(
                tool_results
            ),
            tool_name=(
                "document_search"
            ),
        )
    )

    if document_result is None:
        return WebGapDecision(
            needs_web=False,
            reason=(
                "Local document search did not "
                "complete, so web fallback will "
                "not bypass the local-search "
                "workflow."
            ),
        )

    document_output = (
        _result_output(
            document_result
        )
    )

    sources = (
        document_output.get(
            "sources"
        )
        or []
    )

    sources = [
        source
        for source in sources
        if isinstance(
            source,
            dict,
        )
    ]

    if not sources:
        return WebGapDecision(
            needs_web=True,
            reason=(
                "Uploaded document search "
                "returned no usable evidence."
            ),
            requested_years=sorted(
                requested_years
            ),
            local_source_count=0,
        )

    if asks_for_current:
        return WebGapDecision(
            needs_web=True,
            reason=(
                "The question asks for current "
                "or latest information that may "
                "not exist in the uploaded "
                "document."
            ),
            requested_years=sorted(
                requested_years
            ),
            local_source_count=len(
                sources
            ),
        )

    scores = [
        score
        for score in (
            _source_score(
                source
            )
            for source in sources
        )
        if score is not None
    ]

    if (
        scores
        and max(
            scores
        )
        < settings.document_min_similarity
    ):
        return WebGapDecision(
            needs_web=True,
            reason=(
                "The strongest uploaded-document "
                "retrieval result was below the "
                "configured similarity threshold."
            ),
            requested_years=sorted(
                requested_years
            ),
            local_source_count=len(
                sources
            ),
        )

    return WebGapDecision(
        needs_web=False,
        requested_years=sorted(
            requested_years
        ),
        local_source_count=len(
            sources
        ),
    )