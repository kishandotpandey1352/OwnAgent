import argparse

from app.schemas.web import (
    WebResearchInput,
)

from app.services.serper_search import (
    search_web_with_serper,
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

    parser.add_argument(
        "--max-results",
        type=int,
        default=8,
    )

    args = (
        parser.parse_args()
    )

    result = (
        search_web_with_serper(
            WebResearchInput(
                query=args.query,
                trusted_domains=(
                    args.trusted_domain
                ),
                max_results=(
                    args.max_results
                ),
            )
        )
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )


if __name__ == "__main__":
    main()