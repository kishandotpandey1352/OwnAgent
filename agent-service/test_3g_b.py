import argparse

from app.schemas.facts import (
    FinancialFactExtractionRequest,
)

from app.services.financial_fact_extractor import (
    extract_financial_facts,
)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--document-id",
        required=True,
    )

    parser.add_argument(
        "--company",
        default=None,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    parser.add_argument(
        "--metric",
        action="append",
        default=[],
    )

    args = (
        parser.parse_args()
    )

    request = (
        FinancialFactExtractionRequest(
            document_id=(
                args.document_id
            ),

            company_hint=(
                args.company
            ),

            requested_metrics=(
                args.metric
            ),

            persist=(
                not args.dry_run
            ),

            max_sources=18,

            max_facts=60,
        )
    )

    result = (
        extract_financial_facts(
            user_id=(
                "local-demo-user"
            ),
            request=request,
        )
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()