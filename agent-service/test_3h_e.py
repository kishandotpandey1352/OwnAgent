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

                    extract_structured_facts=True,
                )
            ),
        )
    )

    print(
        "\n=== 3H-E SUMMARY ==="
    )

    print(
        "Citation ready:",
        result.citation_ready,
    )

    print(
        "Structured attempted:",
        result.structured_fact_attempted,
    )

    print(
        "Candidates:",
        result
        .structured_fact_candidate_count,
    )

    print(
        "Persisted:",
        result
        .structured_fact_persisted_count,
    )

    print(
        "Validated:",
        result
        .structured_fact_validated_count,
    )

    print(
        "Rejected:",
        result
        .structured_fact_rejected_count,
    )

    print(
        "Conflicts:",
        result
        .structured_fact_conflict_count,
    )

    print(
        "Structured ready:",
        result.structured_fact_ready,
    )

    print(
        "\n=== VALIDATED WEB FACTS ==="
    )

    for fact in (
        result.validated_facts
    ):
        print(
            (
                f"\n[Web Source "
                f"{fact.source_number}]"
            )
        )

        print(
            "Fact ID:",
            fact.fact_id,
        )

        print(
            "Metric:",
            fact.metric_label,
        )

        print(
            "Canonical:",
            fact.canonical_metric_key,
        )

        print(
            "Raw:",
            fact.raw_value,
        )

        print(
            "Numeric:",
            fact.numeric_value,
        )

        print(
            "Normalized:",
            fact
            .normalized_numeric_value,
        )

        print(
            "Period:",
            fact.period_label,
        )

        print(
            "Validation score:",
            fact.validation_score,
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