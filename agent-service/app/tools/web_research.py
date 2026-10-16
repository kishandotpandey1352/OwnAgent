from __future__ import annotations

from app.core.config import (
    settings,
)

from app.schemas.web import (
    WebResearchInput,
    WebResearchOutput,
)

from app.services.fact_validator import (
    validate_web_facts,
)

from app.services.serper_search import (
    search_web_with_serper,
)

from app.services.web_cache import (
    build_web_fetch_cache_key,
    build_web_search_cache_key,
    get_cached_web_fetch,
    get_cached_web_search,
    set_cached_web_fetch,
    set_cached_web_search,
)

from app.services.web_fact_extractor import (
    extract_web_financial_facts,
    load_validated_web_facts,
)

from app.services.web_request_guard import (
    guard_web_research_request,
)

from app.services.web_source_fetcher import (
    fetch_candidate_sources,
)

from app.services.web_source_ledger import (
    persist_web_citation_sources,
)

from app.services.web_usage_limiter import (
    check_web_usage_limit,
)


# =========================================================
# Web research tool
# =========================================================


def web_research_tool(
    *,
    user_id: str,
    tool_input: WebResearchInput,
) -> WebResearchOutput:
    """
    Execute the complete web-research pipeline.

    Phase 3H-B:
        Serper discovery.

    Phase 3H-C:
        Safe page/PDF fetching and evidence extraction.

    Phase 3H-D:
        Persistent citation-ready web evidence.

    Phase 3H-E:
        Structured web financial fact extraction +
        deterministic validation.

    Phase 3H-F-B:
        Product request limits + hourly Serper quota.

    Phase 3H-F-C:
        Process-local search and fetched-evidence caching.

        IMPORTANT:
        Search cache lookup occurs BEFORE hourly quota
        consumption. A search cache hit therefore does not
        consume another Serper allowance.
    """

    # =====================================================
    # Phase 3H-F-B
    # Product-level web request guard
    # =====================================================

    guarded_request = (
        guard_web_research_request(
            tool_input
        )
    )

    guarded_tool_input = (
        tool_input.model_copy(
            update={
                "query":
                    guarded_request.query,

                "trusted_domains":
                    guarded_request
                    .trusted_domains,

                "max_results":
                    guarded_request
                    .max_results,
            }
        )
    )

    # =====================================================
    # Phase 3H-F-C
    # Search cache
    # =====================================================

    search_cache_hit = False

    search_cache_key = (
        build_web_search_cache_key(
            user_id=user_id,

            query=(
                guarded_request.query
            ),

            trusted_domains=(
                guarded_request
                .trusted_domains
            ),

            max_results=(
                guarded_request
                .max_results
            ),
        )
    )

    search_output = (
        get_cached_web_search(
            key=(
                search_cache_key
            )
        )
    )

    if search_output is not None:
        search_cache_hit = True

        print(
            (
                "[web_research] "
                "SEARCH CACHE HIT"
            ),
            flush=True,
        )

    else:
        print(
            (
                "[web_research] "
                "SEARCH CACHE MISS"
            ),
            flush=True,
        )

        # ================================================
        # Phase 3H-F-B
        #
        # IMPORTANT:
        # Consume quota ONLY on a real provider call.
        # ================================================

        check_web_usage_limit(
            user_id=user_id,
        )

        # ================================================
        # Phase 3H-B
        # Real Serper provider call
        # ================================================

        search_output = (
            search_web_with_serper(
                guarded_tool_input
            )
        )

        # A successful Serper response is cacheable even
        # when it contains zero candidates. This prevents
        # the same no-result query repeatedly consuming API
        # calls during the short search TTL.
        set_cached_web_search(
            key=(
                search_cache_key
            ),

            value=(
                search_output
            ),
        )

    # -----------------------------------------------------
    # No discovery candidates.
    # -----------------------------------------------------

    if not (
        search_output.candidates
    ):
        return (
            search_output
            .model_copy(
                update={
                    "search_cache_hit":
                        search_cache_hit,

                    "fetch_cache_hit":
                        False,
                }
            )
        )

    # =====================================================
    # Phase 3H-C
    # Fetch actual source pages / PDFs
    # =====================================================

    if not (
        settings
        .web_fetch_enabled
    ):
        warnings = list(
            search_output.warnings
        )

        warnings.append(
            (
                "Web search succeeded, but "
                "source fetching is disabled."
            )
        )

        return (
            search_output
            .model_copy(
                update={
                    "search_cache_hit":
                        search_cache_hit,

                    "fetch_cache_hit":
                        False,

                    "warnings":
                        warnings,
                }
            )
        )

    # =====================================================
    # Phase 3H-F-C
    # Fetch/evidence cache
    # =====================================================

    candidate_urls = [
        str(
            candidate.url
        )
        for candidate
        in search_output.candidates
        if getattr(
            candidate,
            "url",
            None,
        )
    ]

    fetch_cache_key = (
        build_web_fetch_cache_key(
            user_id=user_id,

            query=(
                guarded_request.query
            ),

            candidate_urls=(
                candidate_urls
            ),
        )
    )

    cached_fetch_result = (
        get_cached_web_fetch(
            key=(
                fetch_cache_key
            )
        )
    )

    fetch_cache_hit = False

    if (
        cached_fetch_result
        is not None
    ):
        fetch_cache_hit = True

        print(
            (
                "[web_research] "
                "FETCH CACHE HIT"
            ),
            flush=True,
        )

        (
            fetched_sources,
            fetch_failures,
        ) = (
            cached_fetch_result
        )

    else:
        print(
            (
                "[web_research] "
                "FETCH CACHE MISS"
            ),
            flush=True,
        )

        (
            fetched_sources,
            fetch_failures,
        ) = (
            fetch_candidate_sources(
                query=(
                    guarded_request.query
                ),

                candidates=(
                    search_output.candidates
                ),
            )
        )

        # -------------------------------------------------
        # Cache only when at least one source was fetched.
        #
        # Completely failed fetch batches may be temporary
        # network/server problems and should be retried on
        # the next request rather than cached for an hour.
        # -------------------------------------------------

        if fetched_sources:
            set_cached_web_fetch(
                key=(
                    fetch_cache_key
                ),

                value=(
                    (
                        fetched_sources,
                        fetch_failures,
                    )
                ),
            )

    evidence_source_count = sum(
        1
        for source
        in fetched_sources
        if source.evidence_passages
    )

    warnings = list(
        search_output.warnings
    )

    if not fetched_sources:
        warnings.append(
            (
                "Search candidates were "
                "found, but no candidate "
                "source could be fetched "
                "successfully."
            )
        )

    elif (
        evidence_source_count
        == 0
    ):
        warnings.append(
            (
                "Web pages were fetched, "
                "but no relevant evidence "
                "passages were found."
            )
        )

    # =====================================================
    # Phase 3H-D
    # Persist verified evidence into source_ledger
    # =====================================================

    citation_sources = []

    if (
        evidence_source_count
        > 0
    ):
        try:
            citation_sources = (
                persist_web_citation_sources(
                    user_id=(
                        user_id
                    ),

                    fetched_sources=(
                        fetched_sources
                    ),

                    first_source_number=(
                        2001
                    ),
                )
            )

        except Exception as error:
            warnings.append(
                (
                    "Web evidence was fetched "
                    "but could not be persisted "
                    "to source_ledger: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

    citation_ready = bool(
        citation_sources
    )

    if (
        evidence_source_count > 0
        and not citation_ready
    ):
        warnings.append(
            (
                "Fetched web evidence is not "
                "citation-ready because no "
                "persistent source ledger "
                "records were created."
            )
        )

    # =====================================================
    # Phase 3H-E
    # Structured web financial facts
    # =====================================================

    structured_fact_attempted = False

    structured_fact_candidate_count = 0

    structured_fact_persisted_count = 0

    structured_fact_validated_count = 0

    structured_fact_rejected_count = 0

    structured_fact_conflict_count = 0

    validated_facts = []

    if (
        citation_ready
        and (
            guarded_tool_input
            .extract_structured_facts
        )
        and (
            settings
            .web_fact_extraction_enabled
        )
    ):
        structured_fact_attempted = True

        try:
            # =============================================
            # 3H-E-1
            # Structured extraction from citation-ready
            # persisted evidence only.
            # =============================================

            extraction = (
                extract_web_financial_facts(
                    user_id=(
                        user_id
                    ),

                    question=(
                        guarded_request.query
                    ),

                    citation_sources=(
                        citation_sources
                    ),
                )
            )

            structured_fact_candidate_count = (
                extraction
                .candidate_count
            )

            structured_fact_persisted_count = (
                extraction
                .persisted_count
            )

            warnings.extend(
                extraction.warnings
            )

            # =============================================
            # 3H-E-2
            # Deterministic validation.
            # =============================================

            if extraction.fact_ids:
                validation = (
                    validate_web_facts(
                        user_id=(
                            user_id
                        ),

                        fact_ids=(
                            extraction
                            .fact_ids
                        ),
                    )
                )

                structured_fact_validated_count = (
                    validation
                    .validated_count
                )

                structured_fact_rejected_count = (
                    validation
                    .rejected_count
                )

                structured_fact_conflict_count = (
                    validation
                    .conflict_count
                )

                warnings.extend(
                    validation.warnings
                )

                # =========================================
                # 3H-E-3
                # Only validated facts become usable.
                # =========================================

                validated_facts = (
                    load_validated_web_facts(
                        user_id=(
                            user_id
                        ),

                        fact_ids=(
                            extraction
                            .fact_ids
                        ),

                        citation_sources=(
                            citation_sources
                        ),
                    )
                )

            elif (
                extraction.attempted
                and (
                    extraction
                    .candidate_count
                    == 0
                )
            ):
                warnings.append(
                    (
                        "Structured web fact "
                        "extraction completed but "
                        "returned no financial "
                        "fact candidates."
                    )
                )

        except Exception as error:
            # Structured fact processing failure must not
            # destroy successfully retrieved/cited narrative
            # web evidence.
            warnings.append(
                (
                    "Structured web fact "
                    "processing failed: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

    structured_fact_ready = bool(
        validated_facts
    )

    # =====================================================
    # Final WebResearchOutput
    # =====================================================

    return (
        search_output
        .model_copy(
            update={
                # =========================================
                # Phase 3H-C
                # =========================================

                "fetched_source_count":
                    len(
                        fetched_sources
                    ),

                "evidence_source_count":
                    (
                        evidence_source_count
                    ),

                "evidence_ready":
                    (
                        evidence_source_count
                        > 0
                    ),

                "fetched_sources":
                    fetched_sources,

                "fetch_failures":
                    fetch_failures,

                # =========================================
                # Phase 3H-D
                # =========================================

                "citation_ready":
                    citation_ready,

                "citation_source_count":
                    len(
                        citation_sources
                    ),

                "citation_sources":
                    citation_sources,

                # =========================================
                # Phase 3H-E
                # =========================================

                "structured_fact_attempted":
                    (
                        structured_fact_attempted
                    ),

                "structured_fact_ready":
                    (
                        structured_fact_ready
                    ),

                "structured_fact_candidate_count":
                    (
                        structured_fact_candidate_count
                    ),

                "structured_fact_persisted_count":
                    (
                        structured_fact_persisted_count
                    ),

                "structured_fact_validated_count":
                    (
                        structured_fact_validated_count
                    ),

                "structured_fact_rejected_count":
                    (
                        structured_fact_rejected_count
                    ),

                "structured_fact_conflict_count":
                    (
                        structured_fact_conflict_count
                    ),

                "validated_facts":
                    validated_facts,

                # =========================================
                # Phase 3H-F-C
                # =========================================

                "search_cache_hit":
                    search_cache_hit,

                "fetch_cache_hit":
                    fetch_cache_hit,

                # =========================================
                # Combined warnings
                # =========================================

                "warnings":
                    warnings,
            }
        )
    )