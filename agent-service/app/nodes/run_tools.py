from app.graphs.state import FinanceAgentState

from app.schemas.tools import (
    ToolCallRecord,
    ToolCallStatus,
    ToolName,
)

from app.services.web_gap_detector import (
    detect_web_gap,
)

from app.schemas.web import (
    WebResearchInput,
)

from app.tools.registry import (
    run_chart_planner,
    run_csv_profile,
    run_document_search,
    run_financial_calculator,
    run_financial_fact_extractor,
    run_memory_lookup,
    run_web_research,
)

import re
import time
from typing import Any

from app.graphs.state import FinanceAgentState

from app.schemas.tools import (
    ToolCallRecord,
    ToolCallStatus,
    ToolName,
)

from app.services.web_gap_detector import (
    detect_web_gap,
)

from app.schemas.web import (
    WebResearchInput,
)

from app.tools.registry import (
    run_chart_planner,
    run_csv_profile,
    run_document_search,
    run_financial_calculator,
    run_financial_fact_extractor,
    run_memory_lookup,
    run_web_research,
)

# =========================================================
# Financial-fact extraction preflight
# =========================================================


YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


FACT_PREFLIGHT_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "what",
    "which",
    "with",
    "year",
    "years",
    "quarter",
    "quarterly",
}


def _as_output_dict(
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


def _fact_tokens(
    value: str,
) -> set[str]:
    normalized = re.sub(
        r"[^a-z0-9]+",
        " ",
        value.lower(),
    )

    return {
        token
        for token
        in normalized.split()
        if (
            token
            and token
            not in FACT_PREFLIGHT_STOP_WORDS
            and (
                len(token) >= 3
                or token.isdigit()
            )
        )
    }


def _document_search_supports_fact_request(
    *,
    question: str,
    requested_metrics: list[str],
    document_search_output: Any,
) -> tuple[
    bool,
    str | None,
]:
    """
    Avoid launching expensive structured extraction when
    the document search that already ran does not contain
    evidence for the requested metric/period.

    This is intentionally conservative.

    If we cannot inspect the document-search output, allow
    the extractor rather than incorrectly blocking it.
    """

    output = (
        _as_output_dict(
            document_search_output
        )
    )

    if not output:
        return (
            True,
            None,
        )

    sources = (
        output.get(
            "sources"
        )
        or []
    )

    if not isinstance(
        sources,
        list,
    ):
        return (
            True,
            None,
        )

    if not sources:
        return (
            False,
            (
                "Skipped structured financial fact "
                "extraction because document search "
                "returned no source evidence."
            ),
        )

    requested_years = set(
        YEAR_PATTERN.findall(
            question
        )
    )

    metric_token_sets: list[
        set[str]
    ] = []

    for metric in (
        requested_metrics
        or []
    ):
        tokens = (
            _fact_tokens(
                metric
            )
        )

        # Year is a period constraint, not a metric token.
        tokens = {
            token
            for token in tokens
            if not YEAR_PATTERN.fullmatch(
                token
            )
        }

        if tokens:
            metric_token_sets.append(
                tokens
            )

    # If the planner did not supply requested_metrics,
    # do not make a speculative metric decision here.
    if (
        not metric_token_sets
        and not requested_years
    ):
        return (
            True,
            None,
        )

    for source in sources:
        if not isinstance(
            source,
            dict,
        ):
            continue

        snippet = str(
            source.get(
                "snippet"
            )
            or source.get(
                "source_snippet"
            )
            or ""
        )

        if not snippet:
            continue

        snippet_tokens = (
            _fact_tokens(
                snippet
            )
        )

        metric_supported = True

        if metric_token_sets:
            metric_supported = any(
                metric_tokens.issubset(
                    snippet_tokens
                )
                for metric_tokens
                in metric_token_sets
            )

        period_supported = True

        if requested_years:
            snippet_years = set(
                YEAR_PATTERN.findall(
                    snippet
                )
            )

            period_supported = bool(
                requested_years
                .intersection(
                    snippet_years
                )
            )

        if (
            metric_supported
            and period_supported
        ):
            return (
                True,
                None,
            )

    requested_period = (
        ", ".join(
            sorted(
                requested_years
            )
        )
        if requested_years
        else "requested period"
    )

    requested_metric = (
        ", ".join(
            requested_metrics
        )
        if requested_metrics
        else "requested metric"
    )

    return (
        False,
        (
            "Skipped expensive structured financial "
            "fact extraction because retrieved document "
            "evidence did not explicitly support both "
            f"{requested_metric} and {requested_period}."
        ),
    )

def run_tools_node(
    state: FinanceAgentState,
) -> FinanceAgentState:
    tool_plan = state["tool_plan"]

    tool_results: list[
        ToolCallRecord
    ] = []

    document_search_output = None

    # ---------------------------------------------------------
    # 1. Memory lookup
    # ---------------------------------------------------------

    try:
        memory_output = (
            run_memory_lookup(
                state["user_id"]
            )
        )

        tool_results.append(
            ToolCallRecord(
                tool_name=(
                    ToolName.memory_lookup
                ),
                status=(
                    ToolCallStatus.completed
                ),
                input={
                    "user_id":
                        state["user_id"],
                },
                output=memory_output,
            )
        )

    except Exception as error:
        tool_results.append(
            ToolCallRecord(
                tool_name=(
                    ToolName.memory_lookup
                ),
                status=(
                    ToolCallStatus.failed
                ),
                input={
                    "user_id":
                        state["user_id"],
                },
                error=(
                    f"{type(error).__name__}: "
                    f"{error}"
                ),
            )
        )

    # ---------------------------------------------------------
    # 2. Document search
    # ---------------------------------------------------------

    if (
        tool_plan.use_document_search
        and
        tool_plan.document_search_input
    ):
        document_search_input = (
            tool_plan
            .document_search_input
        )

        try:
            document_search_output = (
                run_document_search(
                    state["user_id"],
                    document_search_input,
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .document_search
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        document_search_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        document_search_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .document_search
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        document_search_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

        # ---------------------------------------------------------
    # 3. Financial fact extractor - Phase 3G-D / 3H hardening
    # ---------------------------------------------------------

    if (
        tool_plan
        .use_financial_fact_extractor
        and
        tool_plan
        .financial_fact_extractor_input
    ):
        fact_input = (
            tool_plan
            .financial_fact_extractor_input
        )

        (
            should_run_fact_extractor,
            fact_preflight_reason,
        ) = (
            _document_search_supports_fact_request(
                question=(
                    state["question"]
                ),
                requested_metrics=(
                    fact_input
                    .requested_metrics
                ),
                document_search_output=(
                    document_search_output
                ),
            )
        )

        # -----------------------------------------------------
        # If normal document RAG could not retrieve the
        # requested metric + explicit period, do not launch a
        # second expensive LLM extraction over the document.
        #
        # Empty facts intentionally allow detect_web_gap()
        # below to conclude that local evidence is missing.
        # -----------------------------------------------------

        if not should_run_fact_extractor:
            print(
                (
                    "[run_tools] SKIP "
                    "financial_fact_extractor: "
                    f"{fact_preflight_reason}"
                ),
                flush=True,
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .financial_fact_extractor
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        fact_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output={
                        "ok":
                            True,

                        "query":
                            fact_input.query,

                        "document_summaries":
                            [],

                        "facts":
                            [],

                        "sources":
                            [],

                        "warnings": [
                            fact_preflight_reason
                        ],
                    },
                )
            )

        else:
            fact_started_at = (
                time.perf_counter()
            )

            print(
                (
                    "[run_tools] START "
                    "financial_fact_extractor"
                ),
                flush=True,
            )

            try:
                fact_output = (
                    run_financial_fact_extractor(
                        state["user_id"],
                        fact_input,
                    )
                )

                elapsed = (
                    time.perf_counter()
                    - fact_started_at
                )

                print(
                    (
                        "[run_tools] END "
                        "financial_fact_extractor "
                        f"{elapsed:.2f}s"
                    ),
                    flush=True,
                )

                tool_results.append(
                    ToolCallRecord(
                        tool_name=(
                            ToolName
                            .financial_fact_extractor
                        ),
                        status=(
                            ToolCallStatus
                            .completed
                        ),
                        input=(
                            fact_input
                            .model_dump(
                                mode="json"
                            )
                        ),
                        output=(
                            fact_output
                        ),
                    )
                )

            except Exception as error:
                elapsed = (
                    time.perf_counter()
                    - fact_started_at
                )

                print(
                    (
                        "[run_tools] FAIL "
                        "financial_fact_extractor "
                        f"{elapsed:.2f}s: "
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                    flush=True,
                )

                tool_results.append(
                    ToolCallRecord(
                        tool_name=(
                            ToolName
                            .financial_fact_extractor
                        ),
                        status=(
                            ToolCallStatus
                            .failed
                        ),
                        input=(
                            fact_input
                            .model_dump(
                                mode="json"
                            )
                        ),
                        error=(
                            f"{type(error).__name__}: "
                            f"{error}"
                        ),
                    )
                )
    # ---------------------------------------------------------
    # 4. CSV profile - Phase 3E
    # ---------------------------------------------------------

    if (
        tool_plan.use_csv_profile
        and
        tool_plan.csv_profile_input
    ):
        csv_profile_input = (
            tool_plan
            .csv_profile_input
        )

        try:
            csv_profile_output = (
                run_csv_profile(
                    state["user_id"],
                    csv_profile_input,
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName.csv_profile
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        csv_profile_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        csv_profile_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName.csv_profile
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        csv_profile_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    # ---------------------------------------------------------
    # 5. Financial calculator
    # ---------------------------------------------------------

    if (
        tool_plan
        .use_financial_calculator
        and
        tool_plan
        .financial_calculator_input
    ):
        calculator_input = (
            tool_plan
            .financial_calculator_input
        )

        try:
            calculator_output = (
                run_financial_calculator(
                    calculator_input
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .financial_calculator
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        calculator_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        calculator_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .financial_calculator
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        calculator_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    # ---------------------------------------------------------
    # 6. Chart planner - Phase 3F
    # ---------------------------------------------------------

    if (
        tool_plan.use_chart_planner
        and
        tool_plan.chart_planner_input
    ):
        chart_planner_input = (
            tool_plan
            .chart_planner_input
        )

        try:
            chart_planner_output = (
                run_chart_planner(
                    state["user_id"],
                    chart_planner_input,
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .chart_planner
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        chart_planner_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        chart_planner_output
                    ),
                )
            )

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .chart_planner
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        chart_planner_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    # ---------------------------------------------------------
    # 7. Web fallback - Phase 3H-B
    # ---------------------------------------------------------
    #
    # IMPORTANT:
    #
    # Every local tool has already completed before
    # we evaluate web fallback.
    #
    # Serper is allowed only when:
    #
    #   1. deterministic gap detection says local
    #      evidence is insufficient
    #
    #   AND
    #
    #   2. the user explicitly enabled
    #      allow_web_fallback.
    #
    # Serper results are discovery candidates only
    # in 3H-B.
    # ---------------------------------------------------------

    gap = detect_web_gap(
        question=state["question"],
        use_documents=bool(
            state.get(
                "use_documents",
                False,
            )
        ),
        tool_results=tool_results,
    )

    allow_web_fallback = bool(
        state.get(
            "allow_web_fallback",
            False,
        )
    )

    web_fallback_used = False

    web_fallback_available = bool(
        gap.needs_web
    )

    web_fallback_reason = (
        gap.reason
        if gap.needs_web
        else None
    )

    # ---------------------------------------------------------
    # Run Serper only after local evidence has failed.
    # ---------------------------------------------------------

    if (
        gap.needs_web
        and allow_web_fallback
    ):
        web_input = (
                WebResearchInput(
                    query=(
                        state["question"]
                    ),

                    gap_reason=(
                        gap.reason
                    ),

                    trusted_domains=(
                        state.get(
                            "trusted_web_domains",
                            [],
                        )
                        or []
                    ),

                    max_results=8,

                    # ---------------------------------------------
                    # Phase 3H-E
                    #
                    # Only ask the web pipeline for structured
                    # financial facts if the existing planner
                    # already classified the question as one
                    # requiring the financial fact extractor.
                    # ---------------------------------------------

                    extract_structured_facts=bool(
                        tool_plan
                        .use_web_financial_fact_extractor
                    ),
                )
            )

        try:
            web_output = (
                run_web_research(
                    state["user_id"],
                    web_input,
                )
            )

            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .web_research
                    ),
                    status=(
                        ToolCallStatus
                        .completed
                    ),
                    input=(
                        web_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    output=(
                        web_output
                    ),
                )
            )

            # A real web search was executed.
            web_fallback_used = True

            # The user no longer needs to be prompted
            # to enable fallback for this request.
            web_fallback_available = False

        except Exception as error:
            tool_results.append(
                ToolCallRecord(
                    tool_name=(
                        ToolName
                        .web_research
                    ),
                    status=(
                        ToolCallStatus
                        .failed
                    ),
                    input=(
                        web_input
                        .model_dump(
                            mode="json"
                        )
                    ),
                    error=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

            # =================================================
            # Phase 3H-F-F
            #
            # The internal tool record retains diagnostic
            # information for server-side troubleshooting.
            #
            # Browser/public responses must receive only the
            # safe generic status below.
            # =================================================

            # Search failed, so we have not actually
            # obtained usable web fallback results.
            web_fallback_used = False

            # Fallback is still conceptually available,
            # although this particular attempt failed.
            web_fallback_available = True

            web_fallback_reason = (
                "Public web research was attempted "
                "but could not be completed. "
                "Local evidence remains insufficient."
            )

    # ---------------------------------------------------------
    # Return updated graph state
    # ---------------------------------------------------------

    return {
        **state,

        "tool_results":
            tool_results,

        "web_fallback_used":
            web_fallback_used,

        "web_fallback_available":
            web_fallback_available,

        "web_fallback_reason":
            web_fallback_reason,
    }