from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from app.schemas.web import (
    WebProductResearchSummary,
    WebPublicCitation,
    WebPublicFinancialFact,
)


# =========================================================
# Phase 3H-F-A
# Public response hardening
# =========================================================


MAX_PUBLIC_SNIPPET_CHARS = 1800

MAX_PUBLIC_WARNING_CHARS = 500


# =========================================================
# Generic helpers
# =========================================================


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


def _as_dict(
    value: Any,
) -> dict[str, Any]:
    if isinstance(
        value,
        dict,
    ):
        return value

    if hasattr(
        value,
        "model_dump",
    ):
        dumped = value.model_dump(
            mode="json"
        )

        if isinstance(
            dumped,
            dict,
        ):
            return dumped

    return {}


def _tool_name(
    result: Any,
) -> str:
    data = _as_dict(
        result
    )

    return _enum_value(
        data.get(
            "tool_name"
        )
    )


def _tool_status(
    result: Any,
) -> str:
    data = _as_dict(
        result
    )

    return _enum_value(
        data.get(
            "status"
        )
    )


def _tool_output(
    result: Any,
) -> dict[str, Any]:
    data = _as_dict(
        result
    )

    output = data.get(
        "output"
    )

    if isinstance(
        output,
        dict,
    ):
        return output

    return {}


def _safe_string(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


# =========================================================
# URL validation
# =========================================================


def _is_public_http_url(
    value: str,
) -> bool:
    """
    Product-response validation.

    Safe-web-fetch already performs the real SSRF/network
    security checks.

    This check prevents malformed/non-http provenance URLs
    from being returned as clickable browser links.
    """

    try:
        parsed = urlsplit(
            value
        )

    except ValueError:
        return False

    if parsed.scheme not in {
        "http",
        "https",
    }:
        return False

    if not parsed.hostname:
        return False

    return True


# =========================================================
# Warning sanitization
# =========================================================


def _public_warning(
    value: Any,
) -> str | None:
    """
    Prevent exception/provider/database internals from being
    surfaced directly to the browser.

    Detailed exceptions remain available in backend logs and
    internal tool execution.
    """

    text = _safe_string(
        value
    )

    if not text:
        return None

    lowered = text.lower()

    sensitive_markers = (
        "apikey",
        "api_key",
        "authorization",
        "bearer ",
        "service_role",
        "service-role",
        "traceback",
        "postgres",
        "postgrest",
        "pgrst",
        "apierror",
        "httperror",
        "httpstatuserror",
        "connectionerror",
        "supabase",
    )

    if any(
        marker in lowered
        for marker
        in sensitive_markers
    ):
        return (
            "Web research encountered an "
            "internal processing warning."
        )

    return text[
        :
        MAX_PUBLIC_WARNING_CHARS
    ]


def _collect_public_warnings(
    output: dict[str, Any],
) -> list[str]:
    raw = (
        output.get(
            "warnings"
        )
        or []
    )

    if not isinstance(
        raw,
        list,
    ):
        return []

    warnings: list[str] = []

    for item in raw:
        warning = (
            _public_warning(
                item
            )
        )

        if not warning:
            continue

        if warning in warnings:
            continue

        warnings.append(
            warning
        )

    return warnings


# =========================================================
# Public citations
# =========================================================


def _build_public_citations(
    output: dict[str, Any],
) -> list[
    WebPublicCitation
]:
    if not output.get(
        "citation_ready",
        False,
    ):
        return []

    raw_sources = (
        output.get(
            "citation_sources"
        )
        or []
    )

    if not isinstance(
        raw_sources,
        list,
    ):
        return []

    citations: list[
        WebPublicCitation
    ] = []

    seen_numbers: set[int] = set()

    seen_source_ids: set[str] = set()

    for raw_source in (
        raw_sources
    ):
        if not isinstance(
            raw_source,
            dict,
        ):
            continue

        try:
            source_number = int(
                raw_source.get(
                    "source_number"
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if source_number < 2001:
            continue

        source_id = (
            _safe_string(
                raw_source.get(
                    "source_id"
                )
            )
        )

        url = (
            _safe_string(
                raw_source.get(
                    "url"
                )
            )
        )

        if not source_id:
            continue

        if not (
            _is_public_http_url(
                url
            )
        ):
            continue

        if (
            source_number
            in seen_numbers
        ):
            continue

        if (
            source_id
            in seen_source_ids
        ):
            continue

        snippet = (
            _safe_string(
                raw_source.get(
                    "snippet"
                )
            )
        )

        snippet = snippet[
            :
            MAX_PUBLIC_SNIPPET_CHARS
        ]

        try:
            citation = (
                WebPublicCitation(
                    source_number=(
                        source_number
                    ),

                    source_id=(
                        source_id
                    ),

                    title=(
                        _safe_string(
                            raw_source.get(
                                "title"
                            )
                        )
                        or "Web source"
                    ),

                    url=url,

                    domain=(
                        _safe_string(
                            raw_source.get(
                                "domain"
                            )
                        )
                    ),

                    snippet=(
                        snippet
                    ),

                    page_number=(
                        raw_source.get(
                            "page_number"
                        )
                    ),

                    trust_tier=(
                        raw_source.get(
                            "trust_tier"
                        )
                    ),

                    content_type=(
                        raw_source.get(
                            "content_type"
                        )
                    ),

                    retrieved_at=(
                        _safe_string(
                            raw_source.get(
                                "retrieved_at"
                            )
                        )
                    ),
                )
            )

        except Exception:
            # Malformed internal citation data should not
            # break the entire public agent response.
            continue

        citations.append(
            citation
        )

        seen_numbers.add(
            source_number
        )

        seen_source_ids.add(
            source_id
        )

    return citations


# =========================================================
# Public validated financial facts
# =========================================================


def _build_public_facts(
    *,
    output: dict[str, Any],
    citations: list[
        WebPublicCitation
    ],
) -> list[
    WebPublicFinancialFact
]:
    if not output.get(
        "structured_fact_ready",
        False,
    ):
        return []

    raw_facts = (
        output.get(
            "validated_facts"
        )
        or []
    )

    if not isinstance(
        raw_facts,
        list,
    ):
        return []

    allowed_source_numbers = {
        citation.source_number
        for citation
        in citations
    }

    facts: list[
        WebPublicFinancialFact
    ] = []

    seen_fact_ids: set[str] = set()

    for raw_fact in raw_facts:
        if not isinstance(
            raw_fact,
            dict,
        ):
            continue

        fact_id = (
            _safe_string(
                raw_fact.get(
                    "fact_id"
                )
            )
        )

        if not fact_id:
            continue

        if fact_id in seen_fact_ids:
            continue

        try:
            source_number = int(
                raw_fact.get(
                    "source_number"
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        # The fact cannot be exposed unless its citation is
        # also exposed to the browser.
        if source_number not in (
            allowed_source_numbers
        ):
            continue

        source_ledger_id = (
            _safe_string(
                raw_fact.get(
                    "source_ledger_id"
                )
            )
        )

        if not source_ledger_id:
            continue

        try:
            fact = (
                WebPublicFinancialFact(
                    fact_id=(
                        fact_id
                    ),

                    source_number=(
                        source_number
                    ),

                    source_ledger_id=(
                        source_ledger_id
                    ),

                    company=(
                        raw_fact.get(
                            "company"
                        )
                    ),

                    metric_key=(
                        _safe_string(
                            raw_fact.get(
                                "metric_key"
                            )
                        )
                    ),

                    canonical_metric_key=(
                        _safe_string(
                            raw_fact.get(
                                "canonical_metric_key"
                            )
                        )
                        or _safe_string(
                            raw_fact.get(
                                "metric_key"
                            )
                        )
                    ),

                    metric_label=(
                        _safe_string(
                            raw_fact.get(
                                "metric_label"
                            )
                        )
                        or _safe_string(
                            raw_fact.get(
                                "metric_key"
                            )
                        )
                    ),

                    value_type=(
                        raw_fact.get(
                            "value_type"
                        )
                    ),

                    raw_value=(
                        _safe_string(
                            raw_fact.get(
                                "raw_value"
                            )
                        )
                    ),

                    numeric_value=(
                        raw_fact.get(
                            "numeric_value"
                        )
                    ),

                    normalized_numeric_value=(
                        raw_fact.get(
                            "normalized_numeric_value"
                        )
                    ),

                    currency=(
                        raw_fact.get(
                            "currency"
                        )
                    ),

                    scale=(
                        raw_fact.get(
                            "scale"
                        )
                    ),

                    unit_label=(
                        raw_fact.get(
                            "unit_label"
                        )
                    ),

                    period_label=(
                        raw_fact.get(
                            "period_label"
                        )
                    ),

                    validation_score=float(
                        raw_fact.get(
                            "validation_score",
                            0.0,
                        )
                    ),
                )
            )

        except Exception:
            continue

        facts.append(
            fact
        )

        seen_fact_ids.add(
            fact_id
        )

    return facts


# =========================================================
# Product summary
# =========================================================


def build_web_product_summary(
    *,
    tool_results: list[Any],
    web_fallback_used: bool,
    web_fallback_available: bool,
    web_fallback_reason: str | None,
) -> WebProductResearchSummary:
    """
    Convert INTERNAL WebResearchOutput into a browser-safe
    product contract.

    The browser NEVER receives:
    - candidates
    - raw Serper snippets
    - fetched_sources
    - fetch_failures
    - rejected facts
    - conflict facts
    - pending facts
    """

    searched = False

    evidence_ready = False

    citations: list[
        WebPublicCitation
    ] = []

    validated_facts: list[
        WebPublicFinancialFact
    ] = []

    warnings: list[str] = []

    seen_citation_numbers: set[
        int
    ] = set()

    seen_fact_ids: set[
        str
    ] = set()

    for result in tool_results:
        if (
            _tool_name(
                result
            )
            != "web_research"
        ):
            continue

        if (
            _tool_status(
                result
            )
            != "completed"
        ):
            continue

        output = (
            _tool_output(
                result
            )
        )

        searched = (
            searched
            or bool(
                output.get(
                    "searched",
                    False,
                )
            )
        )

        evidence_ready = (
            evidence_ready
            or bool(
                output.get(
                    "evidence_ready",
                    False,
                )
            )
        )

        result_citations = (
            _build_public_citations(
                output
            )
        )

        for citation in (
            result_citations
        ):
            if (
                citation.source_number
                in seen_citation_numbers
            ):
                continue

            citations.append(
                citation
            )

            seen_citation_numbers.add(
                citation.source_number
            )

        result_facts = (
            _build_public_facts(
                output=output,
                citations=(
                    result_citations
                ),
            )
        )

        for fact in result_facts:
            if fact.fact_id in (
                seen_fact_ids
            ):
                continue

            validated_facts.append(
                fact
            )

            seen_fact_ids.add(
                fact.fact_id
            )

        for warning in (
            _collect_public_warnings(
                output
            )
        ):
            if warning not in warnings:
                warnings.append(
                    warning
                )

    return (
        WebProductResearchSummary(
            used=(
                web_fallback_used
            ),

            available=(
                web_fallback_available
            ),

            reason=(
                web_fallback_reason
            ),

            searched=(
                searched
            ),

            evidence_ready=(
                evidence_ready
            ),

            citation_ready=bool(
                citations
            ),

            structured_fact_ready=bool(
                validated_facts
            ),

            citation_count=len(
                citations
            ),

            validated_fact_count=len(
                validated_facts
            ),

            citations=(
                citations
            ),

            validated_facts=(
                validated_facts
            ),

            warnings=(
                warnings
            ),
        )
    )


# =========================================================
# Public tool-result sanitizer
# =========================================================


def sanitize_tool_results_for_public(
    tool_results: list[Any],
) -> list[
    dict[str, Any]
]:
    """
    Preserve existing non-web tool results for backward
    compatibility.

    web_research is replaced by operational metadata only.

    The actual safe citations/facts are returned separately
    as AgentAnalyzeResponse.web_research.
    """

    public_results: list[
        dict[str, Any]
    ] = []

    for result in tool_results:
        data = _as_dict(
            result
        )

        if not data:
            continue

        if (
            _tool_name(
                result
            )
            != "web_research"
        ):
            public_results.append(
                data
            )

            continue

        output = (
            _tool_output(
                result
            )
        )

        status = (
            _tool_status(
                result
            )
        )

        public_output = {
            # Phase 3H-B
            "provider":
                output.get(
                    "provider"
                ),

            "searched":
                bool(
                    output.get(
                        "searched",
                        False,
                    )
                ),

            "candidate_count":
                int(
                    output.get(
                        "candidate_count",
                        0,
                    )
                    or 0
                ),

            # Phase 3H-C
            "fetched_source_count":
                int(
                    output.get(
                        "fetched_source_count",
                        0,
                    )
                    or 0
                ),

            "evidence_source_count":
                int(
                    output.get(
                        "evidence_source_count",
                        0,
                    )
                    or 0
                ),

            "evidence_ready":
                bool(
                    output.get(
                        "evidence_ready",
                        False,
                    )
                ),

            # Phase 3H-D
            "citation_ready":
                bool(
                    output.get(
                        "citation_ready",
                        False,
                    )
                ),

            "citation_source_count":
                int(
                    output.get(
                        "citation_source_count",
                        0,
                    )
                    or 0
                ),

            # Phase 3H-E
            "structured_fact_attempted":
                bool(
                    output.get(
                        "structured_fact_attempted",
                        False,
                    )
                ),

            "structured_fact_ready":
                bool(
                    output.get(
                        "structured_fact_ready",
                        False,
                    )
                ),

            "structured_fact_candidate_count":
                int(
                    output.get(
                        "structured_fact_candidate_count",
                        0,
                    )
                    or 0
                ),

            "structured_fact_persisted_count":
                int(
                    output.get(
                        "structured_fact_persisted_count",
                        0,
                    )
                    or 0
                ),

            "structured_fact_validated_count":
                int(
                    output.get(
                        "structured_fact_validated_count",
                        0,
                    )
                    or 0
                ),

            "structured_fact_rejected_count":
                int(
                    output.get(
                        "structured_fact_rejected_count",
                        0,
                    )
                    or 0
                ),

            "structured_fact_conflict_count":
                int(
                    output.get(
                        "structured_fact_conflict_count",
                        0,
                    )
                    or 0
                ),

            # Phase 3H-F-C

            "search_cache_hit":
                bool(
                    output.get(
                        "search_cache_hit",
                        False,
                    )
                ),

            "fetch_cache_hit":
                bool(
                    output.get(
                        "fetch_cache_hit",
                        False,
                    )
                ),
        }

        public_results.append(
            {
                "tool_name":
                    "web_research",

                "status":
                    status,

                # Do not expose search query construction,
                # provider parameters or trusted-domain
                # internals through generic tool_results.
                "input":
                    {},

                "output":
                    public_output,

                # Never expose raw provider/database
                # exception strings to the browser.
                "error":
                    (
                        "Web research failed."
                        if status
                        == "failed"
                        else None
                    ),
            }
        )

    return public_results