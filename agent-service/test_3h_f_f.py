from __future__ import annotations

from unittest.mock import (
    patch,
)

from app.core.config import (
    settings,
)
from app.nodes.run_tools import (
    run_tools_node,
)
from app.schemas.tools import (
    ToolPlan,
)
from app.schemas.web import (
    WebEvidencePassage,
    WebFetchedSource,
    WebGapDecision,
    WebProductResearchSummary,
    WebPublicCitation,
    WebResearchInput,
    WebResearchOutput,
    WebSearchCandidate,
)
from app.services.safe_web_fetch import (
    WebFetchError,
    _validate_public_url,
)
from app.services.web_cache import (
    get_web_cache_sizes,
    reset_web_cache_for_testing,
)
from app.services.web_citation_guard import (
    enforce_web_citation_integrity,
)
from app.services.web_product_response import (
    sanitize_tool_results_for_public,
)
from app.services.web_request_guard import (
    WebRequestGuardError,
    guard_web_research_request,
)
from app.services.web_usage_limiter import (
    reset_web_usage_for_testing,
    web_usage_remaining,
)
from app.tools.web_research import (
    web_research_tool,
)


TEST_USER = (
    "3h-f-f-test-user"
)


# =========================================================
# Helpers
# =========================================================


def _assert_raises(
    expected_exception: type[
        BaseException
    ],
    callback,
) -> None:
    try:
        callback()

    except expected_exception:
        return

    raise AssertionError(
        (
            f"Expected "
            f"{expected_exception.__name__} "
            "was not raised."
        )
    )


def _minimal_state(
    *,
    allow_web_fallback: bool,
) -> dict:
    return {
        "request_id":
            "3h-f-f-request",

        "user_id":
            TEST_USER,

        "question":
            (
                "What was Ambac "
                "commission income in 2026?"
            ),

        "tool_plan":
            ToolPlan(
                reason=(
                    "3H-F-F deterministic "
                    "hardening test."
                ),
            ),

        "use_documents":
            True,

        "allow_web_fallback":
            allow_web_fallback,

        "trusted_web_domains":
            [],

        "metadata":
            {},
    }


# =========================================================
# 1. Product limits
# =========================================================


def test_product_limits() -> None:
    print(
        "\n=== F-F LIMITS ==="
    )

    request = (
        WebResearchInput(
            query=(
                "Ambac revenue 2026"
            ),
            trusted_domains=[
                "sec.gov",
                "SEC.GOV",
                "https://ambaccorp.com/",
            ],
            max_results=20,
        )
    )

    guarded = (
        guard_web_research_request(
            request
        )
    )

    assert (
        guarded.max_results
        <= settings
        .web_max_results_per_search
    )

    assert (
        guarded.max_results
        <= settings
        .serper_max_results
    )

    assert (
        guarded.trusted_domains
        == [
            "sec.gov",
            "ambaccorp.com",
        ]
    )

    too_long_length = (
        int(
            settings
            .web_max_query_chars
        )
        + 1
    )

    # WebResearchInput itself has a 4000-char schema cap.
    # The configured product limit is expected to be lower.
    assert (
        too_long_length
        <= 4000
    ), (
        "web_max_query_chars should remain "
        "below the schema's 4000-char ceiling."
    )

    too_long_request = (
        WebResearchInput(
            query=(
                "x"
                * too_long_length
            ),
            max_results=1,
        )
    )

    _assert_raises(
        WebRequestGuardError,
        lambda:
            guard_web_research_request(
                too_long_request
            ),
    )

    max_domains = int(
        settings
        .web_max_trusted_domains
    )

    assert (
        max_domains + 1
        <= 25
    ), (
        "web_max_trusted_domains should "
        "remain below the schema's 25-item "
        "ceiling."
    )

    too_many_domains = (
        WebResearchInput(
            query="Ambac",
            trusted_domains=[
                (
                    f"example"
                    f"{index}.com"
                )
                for index
                in range(
                    max_domains
                    + 1
                )
            ],
            max_results=1,
        )
    )

    _assert_raises(
        WebRequestGuardError,
        lambda:
            guard_web_research_request(
                too_many_domains
            ),
    )

    print(
        "PASS: product limits enforced"
    )


# =========================================================
# 2. Malformed / unsafe URLs
# =========================================================


def test_malformed_urls() -> None:
    print(
        "\n=== F-F MALFORMED URLS ==="
    )

    blocked_urls = [
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://localhost/private",
        "http://127.0.0.1/private",
        "http://user:pass@example.com/",
        "https://example.com:8443/report",
        "https:///missing-host",
    ]

    for url in blocked_urls:
        _assert_raises(
            WebFetchError,
            lambda url=url:
                _validate_public_url(
                    url
                ),
        )

        print(
            "blocked:",
            url,
        )

    print(
        "PASS: malformed/private URLs blocked"
    )


# =========================================================
# 3. Disabled fallback
# =========================================================


def test_disabled_fallback_never_calls_web() -> None:
    print(
        "\n=== F-F DISABLED FALLBACK ==="
    )

    state = (
        _minimal_state(
            allow_web_fallback=False,
        )
    )

    with (
        patch(
            (
                "app.nodes.run_tools."
                "run_memory_lookup"
            ),
            return_value={
                "memory_count": 0,
                "memories": [],
            },
        ),
        patch(
            (
                "app.nodes.run_tools."
                "detect_web_gap"
            ),
            return_value=(
                WebGapDecision(
                    needs_web=True,
                    reason=(
                        "Local evidence "
                        "is insufficient."
                    ),
                )
            ),
        ),
        patch(
            (
                "app.nodes.run_tools."
                "run_web_research"
            ),
        ) as web_mock,
    ):
        result = (
            run_tools_node(
                state
            )
        )

    web_mock.assert_not_called()

    assert (
        result[
            "web_fallback_used"
        ]
        is False
    )

    assert (
        result[
            "web_fallback_available"
        ]
        is True
    )

    print(
        (
            "PASS: fallback OFF never "
            "calls the web provider"
        )
    )


# =========================================================
# 4. Citation hallucination
# =========================================================


def test_citation_hallucination_guard() -> None:
    print(
        "\n=== F-F CITATION GUARD ==="
    )

    summary = (
        WebProductResearchSummary(
            used=True,
            available=False,
            searched=True,
            evidence_ready=True,
            citation_ready=True,
            citation_count=1,
            citations=[
                WebPublicCitation(
                    source_number=2001,
                    source_id=(
                        "source-test-2001"
                    ),
                    title=(
                        "Ambac statutory filings"
                    ),
                    url=(
                        "https://ambaccorp.com/"
                        "statutory-filings/"
                    ),
                    domain=(
                        "ambaccorp.com"
                    ),
                    snippet=(
                        "Ambac 2026 statutory "
                        "filings are listed here."
                    ),
                    page_number=None,
                    trust_tier=(
                        "finance_candidate"
                    ),
                    content_type="html",
                    retrieved_at=(
                        "2026-08-28T00:00:00+00:00"
                    ),
                ),
            ],
        )
    )

    answer = (
        "Valid claim [Web Source 2001]. "
        "Invented claim [Web Source 2999]. "
        "Malformed claim [Web Source abc]."
    )

    guarded = (
        enforce_web_citation_integrity(
            answer=answer,
            web_research=summary,
        )
    )

    assert (
        "[Web Source 2001]"
        in guarded.answer
    )

    assert (
        "[Web Source 2999]"
        not in guarded.answer
    )

    assert (
        "[Web Source abc]"
        not in guarded.answer
    )

    assert (
        guarded.answer.count(
            "[Web citation unavailable]"
        )
        == 2
    )

    assert len(
        guarded.invalid_citations
    ) == 2

    # With zero browser-safe citations, even a numerically
    # well-formed source number must not survive.
    empty_summary = (
        WebProductResearchSummary()
    )

    no_sources = (
        enforce_web_citation_integrity(
            answer=(
                "Claim "
                "[Web Source 2001]."
            ),
            web_research=(
                empty_summary
            ),
        )
    )

    assert (
        "[Web Source 2001]"
        not in no_sources.answer
    )

    print(
        (
            "PASS: hallucinated web "
            "citations cannot survive"
        )
    )


# =========================================================
# 5. Provider failure
# =========================================================


def test_provider_failure_is_safe() -> None:
    print(
        "\n=== F-F PROVIDER FAILURE ==="
    )

    state = (
        _minimal_state(
            allow_web_fallback=True,
        )
    )

    secret_provider_error = (
        "SERPER_SECRET_INTERNAL_FAILURE"
    )

    with (
        patch(
            (
                "app.nodes.run_tools."
                "run_memory_lookup"
            ),
            return_value={
                "memory_count": 0,
                "memories": [],
            },
        ),
        patch(
            (
                "app.nodes.run_tools."
                "detect_web_gap"
            ),
            return_value=(
                WebGapDecision(
                    needs_web=True,
                    reason=(
                        "Local evidence "
                        "is insufficient."
                    ),
                )
            ),
        ),
        patch(
            (
                "app.nodes.run_tools."
                "run_web_research"
            ),
            side_effect=RuntimeError(
                secret_provider_error
            ),
        ) as web_mock,
    ):
        result = (
            run_tools_node(
                state
            )
        )

    web_mock.assert_called_once()

    assert (
        result[
            "web_fallback_used"
        ]
        is False
    )

    assert (
        result[
            "web_fallback_available"
        ]
        is True
    )

    expected_safe_reason = (
        "Public web research was attempted "
        "but could not be completed. "
        "Local evidence remains insufficient."
    )

    assert (
        result[
            "web_fallback_reason"
        ]
        == expected_safe_reason
    ), (
        "Update run_tools.py with the "
        "3H-F-F provider-failure reason."
    )

    public_results = (
        sanitize_tool_results_for_public(
            result.get(
                "tool_results",
                [],
            )
        )
    )

    serialized_public = str(
        public_results
    )

    assert (
        secret_provider_error
        not in serialized_public
    )

    web_public = next(
        item
        for item
        in public_results
        if item.get(
            "tool_name"
        )
        == "web_research"
    )

    assert (
        web_public.get(
            "error"
        )
        == "Web research failed."
    )

    print(
        (
            "PASS: provider failure is "
            "contained and sanitized"
        )
    )


# =========================================================
# 6. Search + fetch cache behavior
# =========================================================


def test_cache_behavior() -> None:
    print(
        "\n=== F-F CACHE BEHAVIOR ==="
    )

    reset_web_cache_for_testing()

    reset_web_usage_for_testing(
        user_id=TEST_USER
    )

    query = (
        "Ambac revenue 2026 "
        "3H-F-F cache test"
    )

    tool_input = (
        WebResearchInput(
            query=query,
            trusted_domains=[],
            max_results=3,
            extract_structured_facts=False,
        )
    )

    search_output = (
        WebResearchOutput(
            query=query,
            searched=True,
            candidate_count=1,
            candidates=[
                WebSearchCandidate(
                    rank=1,
                    original_position=1,
                    title=(
                        "Ambac report"
                    ),
                    url=(
                        "https://example.com/"
                        "ambac-report"
                    ),
                    domain=(
                        "example.com"
                    ),
                    snippet=(
                        "Ambac report"
                    ),
                    trust_tier=(
                        "general_web"
                    ),
                    ranking_score=1.0,
                ),
            ],
        )
    )

    fetched_source = (
        WebFetchedSource(
            search_rank=1,
            title=(
                "Ambac report"
            ),
            requested_url=(
                "https://example.com/"
                "ambac-report"
            ),
            final_url=(
                "https://example.com/"
                "ambac-report"
            ),
            domain=(
                "example.com"
            ),
            content_type="html",
            trust_tier=(
                "general_web"
            ),
            http_status=200,
            text_chars=80,
            evidence_passages=[
                WebEvidencePassage(
                    text=(
                        "Ambac public report "
                        "evidence."
                    ),
                    score=1.0,
                ),
            ],
        )
    )

    before = (
        web_usage_remaining(
            user_id=TEST_USER
        )
    )

    with (
        patch(
            (
                "app.tools.web_research."
                "search_web_with_serper"
            ),
            return_value=(
                search_output
            ),
        ) as search_mock,
        patch(
            (
                "app.tools.web_research."
                "fetch_candidate_sources"
            ),
            return_value=(
                [
                    fetched_source
                ],
                [],
            ),
        ) as fetch_mock,
        patch(
            (
                "app.tools.web_research."
                "persist_web_citation_sources"
            ),
            return_value=[],
        ),
    ):
        first = (
            web_research_tool(
                user_id=TEST_USER,
                tool_input=(
                    tool_input
                ),
            )
        )

        after_first = (
            web_usage_remaining(
                user_id=TEST_USER
            )
        )

        second = (
            web_research_tool(
                user_id=TEST_USER,
                tool_input=(
                    tool_input
                ),
            )
        )

        after_second = (
            web_usage_remaining(
                user_id=TEST_USER
            )
        )

    assert (
        first.search_cache_hit
        is False
    )

    assert (
        first.fetch_cache_hit
        is False
    )

    assert (
        second.search_cache_hit
        is True
    )

    assert (
        second.fetch_cache_hit
        is True
    )

    assert (
        search_mock.call_count
        == 1
    )

    assert (
        fetch_mock.call_count
        == 1
    )

    assert (
        after_first
        == before - 1
    )

    # Search cache hits occur before the limiter, so the
    # repeated request must not consume a second allowance.
    assert (
        after_second
        == after_first
    )

    sizes = (
        get_web_cache_sizes()
    )

    assert (
        sizes[
            "search"
        ]
        >= 1
    )

    assert (
        sizes[
            "fetch"
        ]
        >= 1
    )

    reset_web_cache_for_testing()

    reset_web_usage_for_testing(
        user_id=TEST_USER
    )

    print(
        (
            "PASS: repeat request hits "
            "search/fetch cache without "
            "consuming another quota slot"
        )
    )


# =========================================================
# Runner
# =========================================================


def main() -> None:
    test_product_limits()

    test_malformed_urls()

    test_disabled_fallback_never_calls_web()

    test_citation_hallucination_guard()

    test_provider_failure_is_safe()

    test_cache_behavior()

    print(
        (
            "\nPASS: 3H-F-F end-to-end "
            "hardening checks passed."
        )
    )


if __name__ == "__main__":
    main()
