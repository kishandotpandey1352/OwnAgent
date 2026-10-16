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
                    query=args.query,
                    trusted_domains=(
                        args.trusted_domain
                    ),
                    max_results=8,
                )
            ),
        )
    )

    print(
        "\n=== 3H-D SUMMARY ==="
    )

    print(
        "Search candidates:",
        result.candidate_count,
    )

    print(
        "Fetched:",
        result.fetched_source_count,
    )

    print(
        "Evidence sources:",
        result.evidence_source_count,
    )

    print(
        "Evidence ready:",
        result.evidence_ready,
    )

    print(
        "Citation ready:",
        result.citation_ready,
    )

    print(
        "Citation sources:",
        result.citation_source_count,
    )

    print(
        "\n=== WEB CITATIONS ==="
    )

    for source in (
        result.citation_sources
    ):
        print(
            (
                f"\n[Web Source "
                f"{source.source_number}]"
            )
        )

        print(
            "Source ID:",
            source.source_id,
        )

        print(
            "Title:",
            source.title,
        )

        print(
            "Domain:",
            source.domain,
        )

        print(
            "URL:",
            source.url,
        )

        print(
            "Page:",
            source.page_number,
        )

        print(
            "Trust:",
            source.trust_tier,
        )

        print(
            "Score:",
            source.evidence_score,
        )

        print(
            "Evidence:"
        )

        print(
            source.snippet[
                :
                900
            ]
        )

    if result.warnings:
        print(
            "\n=== WARNINGS ==="
        )

        for warning in (
            result.warnings
        ):
            print(
                "-",
                warning,
            )


if __name__ == "__main__":
    main()