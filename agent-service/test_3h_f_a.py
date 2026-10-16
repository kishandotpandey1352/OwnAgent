from app.services.web_product_response import (
    build_web_product_summary,
    sanitize_tool_results_for_public,
)


def main() -> None:
    # Simulate INTERNAL web_research output.
    #
    # This deliberately contains fields that MUST NOT appear
    # in the generic public tool_results response.
    internal_tool_results = [
        {
            "tool_name": "web_research",
            "status": "completed",
            "input": {
                "query": "Ambac commission income 2025",
                "trusted_domains": [
                    "octavegroup.com",
                ],
            },
            "output": {
                "provider": "serper",
                "searched": True,
                "candidate_count": 4,

                # -----------------------------------------
                # INTERNAL 3H-B data
                # -----------------------------------------
                "candidates": [
                    {
                        "title": "Internal Serper result",
                        "url": "https://example.com/search-result",
                        "snippet": "Discovery-only snippet",
                    }
                ],

                # -----------------------------------------
                # INTERNAL 3H-C data
                # -----------------------------------------
                "fetched_source_count": 2,
                "evidence_source_count": 1,
                "evidence_ready": True,

                "fetched_sources": [
                    {
                        "url": "https://example.com/raw-page",
                        "text": "RAW FETCHED PAGE CONTENT",
                    }
                ],

                "fetch_failures": [
                    {
                        "url": "https://example.com/failure",
                        "error": "Internal fetch error",
                    }
                ],

                # -----------------------------------------
                # 3H-D citation-ready evidence
                # -----------------------------------------
                "citation_ready": True,
                "citation_source_count": 1,

                "citation_sources": [
                    {
                        "source_number": 2001,
                        "source_id": "source-web-test-1",
                        "source_type": "web",
                        "title": "Ambac financial information",
                        "url": "https://www.octavegroup.com/test",
                        "domain": "octavegroup.com",
                        "snippet": (
                            "Commission income information "
                            "from the persisted evidence passage."
                        ),
                        "page_number": None,
                        "trust_tier": "trusted_domain",
                        "provider": "serper",
                        "content_type": "html",
                        "evidence_score": 120.0,
                        "retrieved_at": "2026-08-17T00:00:00Z",
                    }
                ],

                # -----------------------------------------
                # 3H-E operational state
                # -----------------------------------------
                "structured_fact_attempted": True,
                "structured_fact_ready": False,
                "structured_fact_candidate_count": 1,
                "structured_fact_persisted_count": 0,
                "structured_fact_validated_count": 0,
                "structured_fact_rejected_count": 0,
                "structured_fact_conflict_count": 0,

                # This must not leak through generic
                # tool_results either.
                "validated_facts": [],

                "warnings": [],
            },
            "error": None,
        }
    ]

    # =====================================================
    # Build browser-safe web product contract
    # =====================================================

    summary = build_web_product_summary(
        tool_results=internal_tool_results,
        web_fallback_used=True,
        web_fallback_available=False,
        web_fallback_reason=(
            "Uploaded evidence was insufficient."
        ),
    )

    print("\n=== PUBLIC WEB RESEARCH ===")
    print(
        summary.model_dump_json(
            indent=2
        )
    )

    # =====================================================
    # Sanitize generic tool_results
    # =====================================================

    public_tool_results = (
        sanitize_tool_results_for_public(
            internal_tool_results
        )
    )

    print("\n=== SANITIZED TOOL RESULTS ===")

    for result in public_tool_results:
        print(result)

    web_tool = next(
        result
        for result in public_tool_results
        if result.get("tool_name") == "web_research"
    )

    output = web_tool.get(
        "output",
        {}
    )

    forbidden_fields = {
        "candidates",
        "fetched_sources",
        "fetch_failures",
        "citation_sources",
        "validated_facts",
    }

    leaked_fields = (
        forbidden_fields
        .intersection(
            output.keys()
        )
    )

    # =====================================================
    # Assertions
    # =====================================================

    assert not leaked_fields, (
        f"Internal fields leaked: {sorted(leaked_fields)}"
    )

    assert web_tool.get(
        "input"
    ) == {}, (
        "Internal web-research input leaked."
    )

    assert summary.used is True

    assert summary.citation_ready is True

    assert summary.citation_count == 1

    assert len(
        summary.citations
    ) == 1

    assert (
        summary
        .citations[0]
        .source_number
        == 2001
    )

    assert (
        summary
        .citations[0]
        .url
        == "https://www.octavegroup.com/test"
    )

    assert (
        summary
        .structured_fact_ready
        is False
    )

    print(
        "\nPASS: 3H-F-A public response "
        "sanitization works."
    )


if __name__ == "__main__":
    main()