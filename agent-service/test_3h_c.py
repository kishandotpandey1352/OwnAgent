import argparse

from app.schemas.web import (
    WebResearchInput,
)

from app.tools.web_research import (
    web_research_tool,
)


def main() -> None:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--query",
        required=True,
    )

    parser.add_argument(
        "--trusted-domain",
        action="append",
        default=[],
    )

    args = (
        parser.parse_args()
    )

    result = (
        web_research_tool(
            user_id=(
                "local-demo-user"
            ),
            tool_input=(
                WebResearchInput(
                    query=(
                        args.query
                    ),
                    trusted_domains=(
                        args
                        .trusted_domain
                    ),
                    max_results=8,
                )
            ),
        )
    )

    print(
        "\n=== SUMMARY ==="
    )

    print(
        "Candidates:",
        result.candidate_count,
    )

    print(
        "Fetched sources:",
        result
        .fetched_source_count,
    )

    print(
        "Evidence sources:",
        result
        .evidence_source_count,
    )

    print(
        "Evidence ready:",
        result.evidence_ready,
    )

    print(
        "\n=== FETCHED SOURCES ==="
    )

    for source in (
        result.fetched_sources
    ):
        print(
            "\n",
            source.search_rank,
            source.domain,
            source.content_type,
            source.trust_tier,
        )

        print(
            "Title:",
            source.title,
        )

        print(
            "URL:",
            source.final_url,
        )

        for passage in (
            source.evidence_passages
        ):
            print(
                "\nScore:",
                passage.score,
            )

            print(
                "Page:",
                passage.page_number,
            )

            print(
                "Matched:",
                passage.matched_terms,
            )

            print(
                passage.text[
                    :
                    700
                ]
            )

    if result.fetch_failures:
        print(
            "\n=== FETCH FAILURES ==="
        )

        for failure in (
            result.fetch_failures
        ):
            print(
                failure.search_rank,
                failure.url,
                failure.reason,
            )

    print(
        "\n=== FULL OUTPUT ==="
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()