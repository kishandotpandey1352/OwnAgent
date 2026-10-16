import re

from app.graphs.state import FinanceAgentState
from app.schemas.tools import (
    CsvProfileInput,
    DocumentSearchInput,
    FinancialCalculationType,
    FinancialCalculatorInput,
    ToolPlan,
)
from app.schemas.tools import DocumentSearchInput
from app.schemas.chart import ChartRequest
from app.schemas.tools import (
    FinancialFactExtractorInput,
)

NUMBER_PATTERN = re.compile(
    r"-?\d+(?:\.\d+)?"
)

# These are routing cues only.
#
# They do NOT define the universe of allowed financial
# metrics. The extractor remains dynamically typed.

FINANCIAL_FACT_SIGNALS = (
    "revenue",
    "sales",
    "income",
    "earnings",
    "eps",
    "ebitda",
    "cash",
    "debt",
    "asset",
    "liability",
    "equity",
    "margin",
    "ratio",
    "rate",
    "expense",
    "premium",
    "cash flow",
    "capex",
    "free cash flow",
    "backlog",
    "booking",
    "arr",
    "subscriber",
    "customer",
    "occupancy",
    "production",
    "volume",
    "store",
    "employee",
    "financial metric",
    "financial metrics",
    "kpi",
    "key metric",
)


QUANTITATIVE_INTENT_SIGNALS = (
    "what was",
    "what were",
    "how much",
    "how many",
    "value",
    "values",
    "amount",
    "trend",
    "compare",
    "comparison",
    "year over year",
    "year-over-year",
    "quarter",
    "quarterly",
    "annual",
    "by year",
    "by quarter",
    "extract",
)


def _should_use_financial_fact_extractor(
    question: str,
) -> bool:
    lowered = (
        question.lower()
    )

    has_financial_signal = any(
        signal in lowered
        for signal
        in FINANCIAL_FACT_SIGNALS
    )

    has_quantitative_intent = any(
        signal in lowered
        for signal
        in QUANTITATIVE_INTENT_SIGNALS
    )

    # A year or explicit numeric comparison is also
    # a useful structured-finance routing signal.
    contains_year = bool(
        re.search(
            r"\b20\d{2}\b",
            lowered,
        )
    )

    return (
        has_financial_signal
        and (
            has_quantitative_intent
            or contains_year
        )
    )


def _extract_numbers(
    text: str,
) -> list[float]:
    return [
        float(value)
        for value
        in NUMBER_PATTERN.findall(text)
    ]


def plan_tools_node(
    state: FinanceAgentState,
) -> FinanceAgentState:
    question = state["question"]

    document_ids = (
        state.get(
            "document_ids"
        )
        or []
    )

    use_documents = bool(
        state.get(
            "use_documents",
            False,
        )
    )

    use_financial_fact_extractor = (
        use_documents
        and bool(
            document_ids
        )
        and _should_use_financial_fact_extractor(
            question
        )
    )

    use_web_financial_fact_extractor = (
        _should_use_financial_fact_extractor(
            question
        )
    )

    financial_fact_extractor_input = (
        FinancialFactExtractorInput(
            document_ids=(
                document_ids[:3]
            ),
            query=question,
            requested_metrics=[],
            max_facts_per_document=60,
            max_returned_facts=40,
        )
        if use_financial_fact_extractor
        else None
    )

    lowered = question.lower()

    numbers = _extract_numbers(
        question
    )

    # ---------------------------------------------------------
    # Financial calculator planning
    # ---------------------------------------------------------

    use_financial_calculator = False
    calculator_input = None

    reason_parts = [
        "Always check confirmed memory."
    ]

    if any(
        word in lowered
        for word in [
            "growth",
            "increase",
            "decrease",
        ]
    ):
        if len(numbers) >= 2:
            use_financial_calculator = True

            calculator_input = (
                FinancialCalculatorInput(
                    calculation_type=(
                        FinancialCalculationType.growth_rate
                    ),
                    previous_value=numbers[0],
                    current_value=numbers[1],
                )
            )

            reason_parts.append(
                "Detected a growth-rate style "
                "question with two numbers."
            )

    elif any(
        word in lowered
        for word in [
            "margin",
            "ratio",
        ]
    ):
        if len(numbers) >= 2:
            use_financial_calculator = True

            calculator_input = (
                FinancialCalculatorInput(
                    calculation_type=(
                        FinancialCalculationType.margin
                    ),
                    numerator=numbers[0],
                    denominator=numbers[1],
                )
            )

            reason_parts.append(
                "Detected a margin or ratio "
                "question with two numbers."
            )

    elif any(
        word in lowered
        for word in [
            "difference",
            "delta",
            "change",
        ]
    ):
        if len(numbers) >= 2:
            use_financial_calculator = True

            calculator_input = (
                FinancialCalculatorInput(
                    calculation_type=(
                        FinancialCalculationType.delta
                    ),
                    previous_value=numbers[0],
                    current_value=numbers[1],
                )
            )

            reason_parts.append(
                "Detected a delta/change question "
                "with two numbers."
            )

    elif "cagr" in lowered:
        if len(numbers) >= 3:
            use_financial_calculator = True

            calculator_input = (
                FinancialCalculatorInput(
                    calculation_type=(
                        FinancialCalculationType.cagr
                    ),
                    beginning_value=numbers[0],
                    ending_value=numbers[1],
                    periods=numbers[2],
                )
            )

            reason_parts.append(
                "Detected a CAGR question with "
                "beginning, ending, and period values."
            )

    # ---------------------------------------------------------
    # Document search planning - Phase 3D
    # ---------------------------------------------------------

    use_document_search = state.get(
        "use_documents",
        False,
    )

    document_search_input = None

    if use_document_search:
        document_search_input = (
            DocumentSearchInput(
                query=question,
                document_ids=state.get(
                    "document_ids",
                    [],
                ),
                top_k=state.get(
                    "top_k",
                    6,
                ),
            )
        )

        reason_parts.append(
            "Document search was requested."
        )

    # ---------------------------------------------------------
    # CSV profiling planning - Phase 3E
    # ---------------------------------------------------------

    dataset_id = state.get(
        "dataset_id"
    )

    use_csv_profile = bool(
        dataset_id
    )

    csv_profile_input = None

    if dataset_id:
        csv_profile_input = (
            CsvProfileInput(
                dataset_id=dataset_id
            )
        )

        reason_parts.append(
            "A CSV dataset was supplied, "
            "so structured dataset profiling is required."
        )

    # ---------------------------------------------------------
    # Chart planning - Phase 3F
    # ---------------------------------------------------------

    chart_request = state.get(
        "chart_request"
    )

    use_chart_planner = (
        chart_request is not None
    )

    chart_planner_input = None

    if chart_request:
        chart_planner_input = (
            ChartRequest(
                dataset_id=chart_request.dataset_id,
                chart_type=chart_request.chart_type,
                x=chart_request.x,
                series=chart_request.series,
                title=chart_request.title,
                max_rows=chart_request.max_rows,
            )
        )

        reason_parts.append(
            "A structured chart request was supplied, "
            "so a validated chart specification is required."
        )

    return {
        **state,
        "tool_plan": ToolPlan(
            use_memory_lookup=True,

            use_financial_calculator=(
                use_financial_calculator
            ),
            financial_calculator_input=(
                calculator_input
            ),

            use_document_search=(
                use_document_search
            ),
            document_search_input=(
                document_search_input
            ),

            use_csv_profile=(
                use_csv_profile
            ),
            csv_profile_input=(
                csv_profile_input
            ),

            # Phase 3F
            use_chart_planner=(
                use_chart_planner
            ),
            chart_planner_input=(
                chart_planner_input
            ),

            reason=" ".join(
                reason_parts
            ),
            use_financial_fact_extractor=(
                use_financial_fact_extractor
            ),

            use_web_financial_fact_extractor=(
                use_web_financial_fact_extractor
            ),

            financial_fact_extractor_input=(
                financial_fact_extractor_input
            ),
        )
    }