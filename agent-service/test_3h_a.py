from app.services.web_gap_detector import (
    detect_web_gap,
)


def show(
    name: str,
    result,
) -> None:
    print(
        f"\n--- {name} ---"
    )

    print(
        result.model_dump_json(
            indent=2
        )
    )


def main() -> None:
    complete_fact_result = {
        "tool_name":
            "financial_fact_extractor",

        "status":
            "completed",

        "output": {
            "facts": [
                {
                    "metric_label":
                        "Commission income",

                    "period_label":
                        (
                            "Year Ended "
                            "December 31, 2023"
                        ),

                    "numeric_value":
                        "51281",
                }
            ]
        },
    }


    missing_year_result = {
        "tool_name":
            "financial_fact_extractor",

        "status":
            "completed",

        "output": {
            "facts": [
                {
                    "metric_label":
                        "Commission income",

                    "period_label":
                        (
                            "Year Ended "
                            "December 31, 2023"
                        ),

                    "numeric_value":
                        "51281",
                }
            ]
        },
    }


    empty_fact_result = {
        "tool_name":
            "financial_fact_extractor",

        "status":
            "completed",

        "output": {
            "facts": []
        },
    }


    show(
        "covered year",
        detect_web_gap(
            question=(
                "What was commission "
                "income in 2023?"
            ),
            use_documents=True,
            tool_results=[
                complete_fact_result
            ],
        ),
    )


    show(
        "missing year",
        detect_web_gap(
            question=(
                "What was commission "
                "income in 2025?"
            ),
            use_documents=True,
            tool_results=[
                missing_year_result
            ],
        ),
    )


    show(
        "latest information",
        detect_web_gap(
            question=(
                "What is the latest "
                "commission income?"
            ),
            use_documents=True,
            tool_results=[
                complete_fact_result
            ],
        ),
    )


    show(
        "no matching facts",
        detect_web_gap(
            question=(
                "What was commission "
                "income?"
            ),
            use_documents=True,
            tool_results=[
                empty_fact_result
            ],
        ),
    )


if __name__ == "__main__":
    main()