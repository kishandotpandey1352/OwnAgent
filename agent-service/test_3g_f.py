import argparse

from app.services.fact_chart_service import (
    build_document_fact_chart,
)


def main() -> None:
    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--document-id",
        required=True,
    )

    parser.add_argument(
        "--metric-key",
        required=True,
    )

    parser.add_argument(
        "--user-id",
        default="local-demo-user",
    )

    parser.add_argument(
        "--chart-type",
        default="auto",
        choices=[
            "auto",
            "line",
            "bar",
        ],
    )

    args = parser.parse_args()

    result = (
        build_document_fact_chart(
            user_id=args.user_id,
            document_id=(
                args.document_id
            ),
            metric_key=(
                args.metric_key
            ),
            chart_type=(
                args.chart_type
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