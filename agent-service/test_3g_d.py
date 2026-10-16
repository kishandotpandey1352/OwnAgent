import argparse

from app.schemas.tools import (
    FinancialFactExtractorInput,
)

from app.tools.financial_fact_extractor import (
    financial_fact_extractor_tool,
)


def main() -> None:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--document-id",
        action="append",
        required=True,
    )

    parser.add_argument(
        "--query",
        required=True,
    )

    parser.add_argument(
        "--metric",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--user-id",
        default="local-demo-user",
    )

    args = (
        parser.parse_args()
    )

    result = (
        financial_fact_extractor_tool(
            user_id=(
                args.user_id
            ),
            tool_input=(
                FinancialFactExtractorInput(
                    document_ids=(
                        args.document_id
                    ),
                    query=(
                        args.query
                    ),
                    requested_metrics=(
                        args.metric
                    ),
                    max_facts_per_document=60,
                    max_returned_facts=40,
                )
            ),
        )
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()