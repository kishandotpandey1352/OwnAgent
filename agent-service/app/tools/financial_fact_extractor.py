from __future__ import annotations

import re
import time

from decimal import Decimal
from typing import Any

from supabase import (
    Client,
    create_client,
)

from app.core.config import (
    settings,
)

from app.schemas.facts import (
    FinancialFactExtractionRequest,
)

from app.schemas.tools import (
    FinancialFactExtractorInput,
    FinancialFactExtractorOutput,
    FinancialFactToolDocumentSummary,
    FinancialFactToolFact,
    FinancialFactToolSource,
)

from app.services.financial_fact_extractor import (
    extract_financial_facts,
)

from app.services.fact_validator import (
    validate_document_facts,
)


# ============================================================
# Errors
# ============================================================


class FinancialFactToolError(
    RuntimeError,
):
    pass


# ============================================================
# Query relevance
#
# These words are ONLY used for ranking existing facts.
# They are not an allowed metric vocabulary.
# ============================================================


STOP_WORDS = {
    "a",
    "an",
    "and",
    "annual",
    "are",
    "as",
    "at",
    "be",
    "by",
    "compare",
    "comparison",
    "did",
    "do",
    "does",
    "for",
    "from",
    "give",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "of",
    "on",
    "or",
    "quarter",
    "quarterly",
    "show",
    "the",
    "their",
    "this",
    "to",
    "trend",
    "value",
    "values",
    "was",
    "were",
    "what",
    "which",
    "with",
    "year",
    "years",
}


YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


# ============================================================
# Infrastructure
# ============================================================


def _get_supabase_client() -> Client:
    if not settings.supabase_url:
        raise FinancialFactToolError(
            "SUPABASE_URL is required "
            "for financial fact tool execution."
        )

    if (
        not settings
        .supabase_service_role_key
    ):
        raise FinancialFactToolError(
            "SUPABASE_SERVICE_ROLE_KEY "
            "is required for financial "
            "fact tool execution."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


# ============================================================
# Generic helpers
# ============================================================


def _clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .split()
    )


def _normalize_search_text(
    value: Any,
) -> str:
    text = (
        _clean_text(
            value
        )
        .lower()
    )

    text = re.sub(
        r"[^a-z0-9%]+",
        " ",
        text,
    )

    return " ".join(
        text.split()
    )


def _significant_tokens(
    value: Any,
) -> set[str]:
    normalized = (
        _normalize_search_text(
            value
        )
    )

    return {
        token
        for token
        in normalized.split()
        if (
            token
            and token
            not in STOP_WORDS
            and (
                len(token) >= 3
                or token.isdigit()
            )
        )
    }


def _requested_years(
    value: str,
) -> set[str]:
    return set(
        YEAR_PATTERN.findall(
            value
        )
    )


def _metric_query_tokens(
    *,
    query: str,
    requested_metrics: list[str],
) -> set[str]:
    """
    Build tokens used specifically for metric matching.

    When requested_metrics is available, prefer it over the
    entire user question so company names and requested years
    do not dilute metric-match coverage.

    Example:

        query:
            Ambac commission income 2025

        requested_metrics:
            ["commission income"]

        metric tokens:
            {"commission", "income"}

    rather than:

        {"ambac", "commission", "income", "2025"}
    """

    if requested_metrics:
        metric_text = " ".join(
            requested_metrics
        )

        tokens = (
            _significant_tokens(
                metric_text
            )
        )

        tokens = {
            token
            for token in tokens
            if not YEAR_PATTERN.fullmatch(
                token
            )
        }

        if tokens:
            return tokens

    tokens = (
        _significant_tokens(
            query
        )
    )

    return {
        token
        for token in tokens
        if not YEAR_PATTERN.fullmatch(
            token
        )
    }


def _fact_period_matches_query(
    *,
    row: dict[str, Any],
    query: str,
) -> bool:
    """
    Prevent an exact metric from the wrong period from being
    reused for a question containing an explicit year.

    Example:

        requested:
            commission income 2025

        existing fact:
            commission income 2024

        result:
            False
    """

    requested_years = (
        _requested_years(
            query
        )
    )

    if not requested_years:
        return True

    fact_period_text = " ".join(
        [
            _clean_text(
                row.get(
                    "period_label"
                )
            ),
            _clean_text(
                row.get(
                    "period_start"
                )
            ),
            _clean_text(
                row.get(
                    "period_end"
                )
            ),
        ]
    )

    fact_years = (
        _requested_years(
            fact_period_text
        )
    )

    if not fact_years:
        return False

    return bool(
        requested_years
        .intersection(
            fact_years
        )
    )


def _as_decimal(
    value: Any,
) -> Decimal | None:
    if (
        value is None
        or value == ""
    ):
        return None

    try:
        return Decimal(
            str(value)
        )

    except Exception:
        return None


# ============================================================
# Existing validated facts
# ============================================================


def _load_validated_fact_rows(
    *,
    client: Client,
    user_id: str,
    document_id: str,
) -> list[
    dict[str, Any]
]:
    response = (
        client
        .table(
            "analysis_facts"
        )
        .select(
            (
                "id,"
                "document_id,"
                "source_ledger_id,"
                "company,"
                "metric_key,"
                "canonical_metric_key,"
                "metric_label,"
                "value_type,"
                "numeric_value,"
                "normalized_numeric_value,"
                "text_value,"
                "raw_value,"
                "unit_key,"
                "unit_label,"
                "currency,"
                "scale,"
                "period_label,"
                "period_start,"
                "period_end,"
                "category,"
                "statement_type,"
                "validation_score,"
                "validation_status"
            )
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
        .eq(
            "validation_status",
            "validated",
        )
        .execute()
    )

    return (
        response.data
        or []
    )


def _load_status_counts(
    *,
    client: Client,
    user_id: str,
    document_id: str,
) -> dict[str, int]:
    response = (
        client
        .table(
            "analysis_facts"
        )
        .select(
            "validation_status"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
        .execute()
    )

    counts = {
        "pending": 0,
        "validated": 0,
        "rejected": 0,
        "conflict": 0,
    }

    for row in (
        response.data
        or []
    ):
        status = str(
            row.get(
                "validation_status",
                "",
            )
        )

        if status in counts:
            counts[
                status
            ] += 1

    return counts


# ============================================================
# Existing-fact relevance
# ============================================================


def _fact_matches_query(
    *,
    row: dict[str, Any],
    query: str,
    requested_metrics: list[str],
) -> bool:
    """
    Determine whether a previously validated fact can satisfy
    the current request.

    Metric matching and period matching are intentionally
    handled separately.

    This fixes the previous problem where:

        Ambac + commission + income + 2025

    was compared against:

        commission + income

    causing a correct cached fact to miss the lexical
    threshold.
    """

    metric_query_tokens = (
        _metric_query_tokens(
            query=query,
            requested_metrics=(
                requested_metrics
            ),
        )
    )

    if not metric_query_tokens:
        return False

    fact_text = " ".join(
        [
            _clean_text(
                row.get(
                    "metric_key"
                )
            ),
            _clean_text(
                row.get(
                    "canonical_metric_key"
                )
            ),
            _clean_text(
                row.get(
                    "metric_label"
                )
            ),
        ]
    )

    fact_tokens = (
        _significant_tokens(
            fact_text
        )
    )

    overlap = (
        metric_query_tokens
        .intersection(
            fact_tokens
        )
    )

    if not overlap:
        return False

    # Explicit requested years must also match the fact
    # period.
    if not (
        _fact_period_matches_query(
            row=row,
            query=query,
        )
    ):
        return False

    if (
        len(
            metric_query_tokens
        )
        == 1
    ):
        return True

    coverage = (
        len(
            overlap
        )
        / len(
            metric_query_tokens
        )
    )

    return (
        coverage >= 0.66
    )


def _fact_relevance_score(
    *,
    row: dict[str, Any],
    query: str,
    requested_metrics: list[str],
) -> float:
    metric_query_tokens = (
        _metric_query_tokens(
            query=query,
            requested_metrics=(
                requested_metrics
            ),
        )
    )

    if not metric_query_tokens:
        return 0.0

    fact_metric_text = " ".join(
        [
            _clean_text(
                row.get(
                    "metric_key"
                )
            ),
            _clean_text(
                row.get(
                    "canonical_metric_key"
                )
            ),
            _clean_text(
                row.get(
                    "metric_label"
                )
            ),
        ]
    )

    fact_tokens = (
        _significant_tokens(
            fact_metric_text
        )
    )

    overlap = (
        metric_query_tokens
        .intersection(
            fact_tokens
        )
    )

    if not overlap:
        return 0.0

    if not (
        _fact_period_matches_query(
            row=row,
            query=query,
        )
    ):
        return 0.0

    coverage = (
        len(
            overlap
        )
        / max(
            1,
            len(
                metric_query_tokens
            ),
        )
    )

    score = (
        float(
            len(
                overlap
            )
        )
        + coverage
    )

    normalized_label = (
        _normalize_search_text(
            row.get(
                "metric_label"
            )
        )
    )

    normalized_requested_metrics = (
        _normalize_search_text(
            " ".join(
                requested_metrics
            )
        )
    )

    if (
        normalized_label
        and normalized_requested_metrics
        and (
            normalized_label
            in normalized_requested_metrics
            or normalized_requested_metrics
            in normalized_label
        )
    ):
        score += 3.0

    canonical_key = (
        _normalize_search_text(
            row.get(
                "canonical_metric_key"
            )
        )
    )

    if (
        canonical_key
        and normalized_requested_metrics
        and canonical_key
        in normalized_requested_metrics
    ):
        score += 2.0

    validation_score = float(
        row.get(
            "validation_score"
        )
        or 0.0
    )

    score += (
        max(
            0.0,
            min(
                validation_score,
                1.0,
            ),
        )
        * 0.25
    )

    return score


def _rank_relevant_rows(
    *,
    rows: list[
        dict[str, Any]
    ],
    query: str,
    requested_metrics: list[str],
) -> list[
    dict[str, Any]
]:
    ranked: list[
        tuple[
            float,
            dict[str, Any],
        ]
    ] = []

    for row in rows:
        if not (
            _fact_matches_query(
                row=row,
                query=query,
                requested_metrics=(
                    requested_metrics
                ),
            )
        ):
            continue

        score = (
            _fact_relevance_score(
                row=row,
                query=query,
                requested_metrics=(
                    requested_metrics
                ),
            )
        )

        ranked.append(
            (
                score,
                row,
            )
        )

    ranked.sort(
        key=lambda item: (
            item[0],
            float(
                item[1].get(
                    "validation_score"
                )
                or 0.0
            ),
        ),
        reverse=True,
    )

    return [
        row
        for (
            _score,
            row,
        ) in ranked
    ]


# ============================================================
# Source ledger loading
# ============================================================


def _load_source_rows(
    *,
    client: Client,
    user_id: str,
    source_ledger_ids: list[str],
) -> dict[
    str,
    dict[str, Any],
]:
    if not source_ledger_ids:
        return {}

    response = (
        client
        .table(
            "source_ledger"
        )
        .select(
            (
                "id,"
                "document_id,"
                "chunk_id,"
                "source_title,"
                "page_number,"
                "source_snippet,"
                "retrieval_score"
            )
        )
        .eq(
            "user_id",
            user_id,
        )
        .in_(
            "id",
            source_ledger_ids,
        )
        .execute()
    )

    return {
        str(
            row["id"]
        ): row
        for row
        in (
            response.data
            or []
        )
    }


# ============================================================
# Extraction + validation
# ============================================================


def _extract_and_validate_document(
    *,
    user_id: str,
    document_id: str,
    tool_input: FinancialFactExtractorInput,
) -> tuple[
    FinancialFactToolDocumentSummary,
    list[
        dict[str, Any]
    ],
]:
    """
    Run structured financial-fact extraction for one
    document and validate newly persisted candidates.

    This path is intentionally bounded for interactive
    /agents/analyze latency.

    The broader document search performed before this tool
    should already have determined that structured extraction
    is worthwhile.
    """

    # --------------------------------------------------------
    # Extraction
    # --------------------------------------------------------

    extraction_started = (
        time.perf_counter()
    )

    print(
        (
            "[financial_fact_extractor] "
            f"START extraction "
            f"{document_id}"
        ),
        flush=True,
    )

    extraction = (
        extract_financial_facts(
            user_id=user_id,
            request=(
                FinancialFactExtractionRequest(
                    document_id=(
                        document_id
                    ),

                    company_hint=None,

                    requested_metrics=(
                        tool_input
                        .requested_metrics
                    ),

                    focus_queries=[
                        tool_input.query
                    ],

                    # ------------------------------------
                    # Interactive latency budget
                    #
                    # Previous values:
                    #   top_k_per_query = 8
                    #   max_sources     = 24
                    #
                    # Those values can make an interactive
                    # request unnecessarily expensive.
                    # ------------------------------------

                    top_k_per_query=4,

                    max_sources=8,

                    max_facts=max(
                        1,
                        min(
                            tool_input
                            .max_facts_per_document,
                            12,
                        ),
                    ),

                    include_text_facts=False,

                    persist=True,
                )
            ),
        )
    )

    extraction_elapsed = (
        time.perf_counter()
        - extraction_started
    )

    print(
        (
            "[financial_fact_extractor] "
            f"END extraction "
            f"{document_id} "
            f"{extraction_elapsed:.2f}s "
            f"candidates="
            f"{extraction.candidate_count} "
            f"persisted="
            f"{extraction.persisted_count}"
        ),
        flush=True,
    )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    validation_warnings: list[str] = []

    processed_count = 0

    validated_count = 0

    rejected_count = 0

    conflict_count = 0

    # Do not run a document-wide validator when extraction
    # produced nothing new.
    if (
        extraction.persisted_count
        > 0
    ):
        validation_started = (
            time.perf_counter()
        )

        print(
            (
                "[financial_fact_extractor] "
                f"START validation "
                f"{document_id}"
            ),
            flush=True,
        )

        validation = (
            validate_document_facts(
                user_id=user_id,
                document_id=document_id,
                revalidate=False,
            )
        )

        validation_elapsed = (
            time.perf_counter()
            - validation_started
        )

        print(
            (
                "[financial_fact_extractor] "
                f"END validation "
                f"{document_id} "
                f"{validation_elapsed:.2f}s "
                f"processed="
                f"{validation.processed_count} "
                f"validated="
                f"{validation.validated_count} "
                f"rejected="
                f"{validation.rejected_count} "
                f"conflicts="
                f"{validation.conflict_count}"
            ),
            flush=True,
        )

        processed_count = (
            validation
            .processed_count
        )

        validated_count = (
            validation
            .validated_count
        )

        rejected_count = (
            validation
            .rejected_count
        )

        conflict_count = (
            validation
            .conflict_count
        )

        validation_warnings.extend(
            validation.warnings
        )

    else:
        validation_warnings.append(
            (
                "No new financial fact "
                "candidates were persisted; "
                "document-wide validation was "
                "not rerun."
            )
        )

    # --------------------------------------------------------
    # Tool summary
    # --------------------------------------------------------

    summary = (
        FinancialFactToolDocumentSummary(
            document_id=(
                document_id
            ),

            ok=True,

            extraction_performed=True,

            extracted_count=(
                extraction
                .candidate_count
            ),

            persisted_count=(
                extraction
                .persisted_count
            ),

            processed_count=(
                processed_count
            ),

            validated_count=(
                validated_count
            ),

            rejected_count=(
                rejected_count
            ),

            conflict_count=(
                conflict_count
            ),

            warnings=[
                *extraction.warnings,
                *validation_warnings,
            ],
        )
    )

    # --------------------------------------------------------
    # Reload all currently validated facts for this document.
    #
    # _build_output() applies the metric/period relevance
    # filter afterward.
    # --------------------------------------------------------

    client = (
        _get_supabase_client()
    )

    rows = (
        _load_validated_fact_rows(
            client=client,
            user_id=user_id,
            document_id=document_id,
        )
    )

    return (
        summary,
        rows,
    )


# ============================================================
# Output building
# ============================================================


def _build_output(
    *,
    client: Client,
    user_id: str,
    tool_input: FinancialFactExtractorInput,
    summaries: list[
        FinancialFactToolDocumentSummary
    ],
    fact_rows: list[
        dict[str, Any]
    ],
    warnings: list[str],
) -> FinancialFactExtractorOutput:
    # --------------------------------------------------------
    # Rank facts by metric + period relevance.
    # --------------------------------------------------------

    ranked_rows = sorted(
        fact_rows,
        key=lambda row: (
            _fact_relevance_score(
                row=row,
                query=(
                    tool_input.query
                ),
                requested_metrics=(
                    tool_input
                    .requested_metrics
                ),
            ),
            float(
                row.get(
                    "validation_score"
                )
                or 0.0
            ),
        ),
        reverse=True,
    )

    relevant_rows = [
        row
        for row in ranked_rows
        if (
            _fact_matches_query(
                row=row,
                query=(
                    tool_input.query
                ),
                requested_metrics=(
                    tool_input
                    .requested_metrics
                ),
            )
        )
    ]

    selected_rows = (
        relevant_rows[
            :
            tool_input
            .max_returned_facts
        ]
    )

    if not selected_rows:
        warnings.append(
            (
                "No validated financial fact "
                "matched the requested metric "
                "and period."
            )
        )

    # --------------------------------------------------------
    # Load provenance only for facts actually being returned.
    # --------------------------------------------------------

    source_ids = list(
        {
            str(
                row[
                    "source_ledger_id"
                ]
            )
            for row in selected_rows
            if row.get(
                "source_ledger_id"
            )
        }
    )

    source_map = (
        _load_source_rows(
            client=client,
            user_id=user_id,
            source_ledger_ids=(
                source_ids
            ),
        )
    )

    # Start at 1001 so structured document-fact citations do
    # not collide with normal RAG [Source 1], [Source 2], etc.
    source_number_map: dict[
        str,
        int,
    ] = {}

    sources: list[
        FinancialFactToolSource
    ] = []

    next_source_number = 1001

    # --------------------------------------------------------
    # Build source objects
    # --------------------------------------------------------

    for row in selected_rows:
        source_id = str(
            row.get(
                "source_ledger_id"
            )
            or ""
        )

        if (
            not source_id
            or source_id
            in source_number_map
        ):
            continue

        source = (
            source_map.get(
                source_id
            )
        )

        if source is None:
            continue

        source_number_map[
            source_id
        ] = (
            next_source_number
        )

        sources.append(
            FinancialFactToolSource(
                source_number=(
                    next_source_number
                ),

                source_ledger_id=(
                    source_id
                ),

                document_id=str(
                    source.get(
                        "document_id",
                        "",
                    )
                ),

                chunk_id=(
                    str(
                        source.get(
                            "chunk_id"
                        )
                    )
                    if source.get(
                        "chunk_id"
                    )
                    else None
                ),

                source_title=(
                    _clean_text(
                        source.get(
                            "source_title"
                        )
                    )
                    or None
                ),

                page_number=(
                    source.get(
                        "page_number"
                    )
                ),

                source_snippet=(
                    _clean_text(
                        source.get(
                            "source_snippet"
                        )
                    )
                ),

                retrieval_score=(
                    float(
                        source.get(
                            "retrieval_score"
                        )
                    )
                    if (
                        source.get(
                            "retrieval_score"
                        )
                        is not None
                    )
                    else None
                ),
            )
        )

        next_source_number += 1

    # --------------------------------------------------------
    # Build fact objects
    # --------------------------------------------------------

    facts: list[
        FinancialFactToolFact
    ] = []

    for row in selected_rows:
        source_id = str(
            row.get(
                "source_ledger_id"
            )
            or ""
        )

        source_number = (
            source_number_map.get(
                source_id
            )
        )

        # A validated fact without usable provenance must not
        # be exposed to the answer model.
        if source_number is None:
            warnings.append(
                (
                    "Skipped validated fact "
                    f"{row.get('id')} because "
                    "its source ledger entry "
                    "could not be loaded."
                )
            )

            continue

        facts.append(
            FinancialFactToolFact(
                fact_id=str(
                    row[
                        "id"
                    ]
                ),

                document_id=str(
                    row[
                        "document_id"
                    ]
                ),

                source_number=(
                    source_number
                ),

                company=(
                    _clean_text(
                        row.get(
                            "company"
                        )
                    )
                    or None
                ),

                metric_key=str(
                    row.get(
                        "metric_key",
                        "",
                    )
                ),

                canonical_metric_key=(
                    _clean_text(
                        row.get(
                            "canonical_metric_key"
                        )
                    )
                    or None
                ),

                metric_label=str(
                    row.get(
                        "metric_label",
                        "",
                    )
                ),

                value_type=str(
                    row.get(
                        "value_type",
                        "",
                    )
                ),

                numeric_value=(
                    _as_decimal(
                        row.get(
                            "numeric_value"
                        )
                    )
                ),

                normalized_numeric_value=(
                    _as_decimal(
                        row.get(
                            "normalized_numeric_value"
                        )
                    )
                ),

                text_value=(
                    _clean_text(
                        row.get(
                            "text_value"
                        )
                    )
                    or None
                ),

                raw_value=str(
                    row.get(
                        "raw_value",
                        "",
                    )
                ),

                unit_key=(
                    _clean_text(
                        row.get(
                            "unit_key"
                        )
                    )
                    or None
                ),

                unit_label=(
                    _clean_text(
                        row.get(
                            "unit_label"
                        )
                    )
                    or None
                ),

                currency=(
                    _clean_text(
                        row.get(
                            "currency"
                        )
                    )
                    or None
                ),

                scale=(
                    _clean_text(
                        row.get(
                            "scale"
                        )
                    )
                    or None
                ),

                period_label=(
                    _clean_text(
                        row.get(
                            "period_label"
                        )
                    )
                    or None
                ),

                period_start=(
                    row.get(
                        "period_start"
                    )
                ),

                period_end=(
                    row.get(
                        "period_end"
                    )
                ),

                category=(
                    _clean_text(
                        row.get(
                            "category"
                        )
                    )
                    or None
                ),

                statement_type=(
                    _clean_text(
                        row.get(
                            "statement_type"
                        )
                    )
                    or None
                ),

                validation_score=(
                    float(
                        row.get(
                            "validation_score"
                        )
                    )
                    if (
                        row.get(
                            "validation_score"
                        )
                        is not None
                    )
                    else None
                ),
            )
        )

    return (
        FinancialFactExtractorOutput(
            ok=any(
                summary.ok
                for summary
                in summaries
            ),

            query=(
                tool_input.query
            ),

            document_summaries=(
                summaries
            ),

            facts=(
                facts
            ),

            sources=(
                sources
            ),

            warnings=(
                warnings
            ),
        )
    )


# ============================================================
# Public tool
# ============================================================


def financial_fact_extractor_tool(
    *,
    user_id: str,
    tool_input: FinancialFactExtractorInput,
) -> FinancialFactExtractorOutput:
    """
    Return validated, source-backed financial facts.

    The tool first attempts to reuse an existing validated fact
    matching both the requested metric and explicit period.

    Only if no suitable validated fact exists does it run the
    more expensive structured extraction path.
    """

    client = (
        _get_supabase_client()
    )

    summaries: list[
        FinancialFactToolDocumentSummary
    ] = []

    all_rows: list[
        dict[str, Any]
    ] = []

    warnings: list[str] = []

    for document_id in (
        tool_input.document_ids
    ):
        document_started = (
            time.perf_counter()
        )

        print(
            (
                "[financial_fact_extractor] "
                f"START document "
                f"{document_id}"
            ),
            flush=True,
        )

        try:
            # ------------------------------------------------
            # First attempt:
            # reuse an existing validated metric + period fact.
            # ------------------------------------------------

            existing_rows = (
                _load_validated_fact_rows(
                    client=client,
                    user_id=user_id,
                    document_id=(
                        document_id
                    ),
                )
            )

            relevant_existing = (
                _rank_relevant_rows(
                    rows=(
                        existing_rows
                    ),
                    query=(
                        tool_input.query
                    ),
                    requested_metrics=(
                        tool_input
                        .requested_metrics
                    ),
                )
            )

            if relevant_existing:
                counts = (
                    _load_status_counts(
                        client=client,
                        user_id=user_id,
                        document_id=(
                            document_id
                        ),
                    )
                )

                summaries.append(
                    FinancialFactToolDocumentSummary(
                        document_id=(
                            document_id
                        ),

                        ok=True,

                        extraction_performed=False,

                        extracted_count=0,

                        persisted_count=0,

                        processed_count=0,

                        validated_count=(
                            counts[
                                "validated"
                            ]
                        ),

                        rejected_count=(
                            counts[
                                "rejected"
                            ]
                        ),

                        conflict_count=(
                            counts[
                                "conflict"
                            ]
                        ),

                        warnings=[
                            (
                                "Reused existing "
                                "validated financial facts."
                            )
                        ],
                    )
                )

                all_rows.extend(
                    relevant_existing
                )

                elapsed = (
                    time.perf_counter()
                    - document_started
                )

                print(
                    (
                        "[financial_fact_extractor] "
                        f"REUSED document "
                        f"{document_id} "
                        f"{elapsed:.2f}s "
                        f"facts="
                        f"{len(relevant_existing)}"
                    ),
                    flush=True,
                )

                continue

            # ------------------------------------------------
            # Cache miss:
            # perform bounded extraction + validation.
            # ------------------------------------------------

            (
                summary,
                extracted_rows,
            ) = (
                _extract_and_validate_document(
                    user_id=user_id,
                    document_id=(
                        document_id
                    ),
                    tool_input=(
                        tool_input
                    ),
                )
            )

            summaries.append(
                summary
            )

            all_rows.extend(
                extracted_rows
            )

            elapsed = (
                time.perf_counter()
                - document_started
            )

            print(
                (
                    "[financial_fact_extractor] "
                    f"END document "
                    f"{document_id} "
                    f"{elapsed:.2f}s"
                ),
                flush=True,
            )

        except Exception as error:
            elapsed = (
                time.perf_counter()
                - document_started
            )

            error_message = (
                f"Financial fact processing "
                f"failed for {document_id}: "
                f"{type(error).__name__}: "
                f"{error}"
            )

            print(
                (
                    "[financial_fact_extractor] "
                    f"FAIL document "
                    f"{document_id} "
                    f"{elapsed:.2f}s: "
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
                flush=True,
            )

            summaries.append(
                FinancialFactToolDocumentSummary(
                    document_id=(
                        document_id
                    ),

                    ok=False,

                    error=(
                        error_message
                    ),
                )
            )

            warnings.append(
                error_message
            )

    return (
        _build_output(
            client=client,
            user_id=user_id,
            tool_input=(
                tool_input
            ),
            summaries=(
                summaries
            ),
            fact_rows=(
                all_rows
            ),
            warnings=(
                warnings
            ),
        )
    )