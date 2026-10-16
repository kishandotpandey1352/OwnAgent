from app.schemas.tools import (
    AuditLogInput,
    CsvProfileInput,
    DocumentSearchInput,
    FinancialCalculatorInput,
    FinancialFactExtractorInput,
    ToolDefinition,
    ToolName,
    ToolRiskLevel,
)
from app.tools.audit import audit_log_tool
from app.tools.document_search import document_search_tool
from app.tools.financial_calculator import financial_calculator_tool
from app.tools.memory import memory_lookup_tool
from app.tools.csv_profile import profile_csv_dataset
from app.schemas.chart import ChartRequest
from app.tools.chart_planner import build_chart_spec
from app.tools.financial_fact_extractor import (
    financial_fact_extractor_tool,
)

from app.schemas.web import (
    WebResearchInput,
)

from app.tools.web_research import (
    web_research_tool,
)

TOOL_REGISTRY: dict[ToolName, ToolDefinition] = {
    ToolName.memory_lookup: ToolDefinition(
        name=ToolName.memory_lookup,
        description="Read confirmed user preference memory.",
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),

    ToolName.financial_calculator: ToolDefinition(
        name=ToolName.financial_calculator,
        description=(
            "Calculate growth, margin, delta, percentage, or CAGR."
        ),
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),

    ToolName.audit_log: ToolDefinition(
        name=ToolName.audit_log,
        description="Write an agent audit event.",
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),

    ToolName.document_search: ToolDefinition(
        name=ToolName.document_search,
        description=(
            "Search indexed user documents and return source-backed "
            "chunks ranked by semantic similarity."
        ),
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),

    # Phase 3E
    ToolName.csv_profile: ToolDefinition(
        name=ToolName.csv_profile,
        description=(
            "Profile an uploaded CSV dataset using deterministic "
            "structured-data analysis. Returns column types, missing "
            "values, numeric statistics, sample rows, and chart suggestions."
        ),
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),

    # Phase 3F-B
    ToolName.chart_planner: ToolDefinition(
        name=ToolName.chart_planner,
        description=(
            "Build a validated chart specification from an uploaded "
            "structured dataset. Validates columns, parses financial "
            "numeric values, prepares chart-safe data, and reports "
            "source coverage and warnings."
        ),
        risk_level=ToolRiskLevel.low,
        requires_confirmation=False,
        allowed_in_background=True,
    ),

    ToolName.financial_fact_extractor:ToolDefinition(
        name=(
            ToolName
            .financial_fact_extractor
        ),
        description=(
            "Retrieve or extract "
            "source-backed validated "
            "financial facts from "
            "selected documents."
        ),
        risk_level=(
            ToolRiskLevel.medium
        ),
        requires_confirmation=False,
        allowed_in_background=True,
    ),
    ToolName.web_research:
    ToolDefinition(
        name=ToolName.web_research,
        description=(
            "Search public web results "
            "using Serper only after "
            "uploaded-document evidence "
            "has been determined to be "
            "insufficient and web fallback "
            "was explicitly allowed."
        ),
        risk_level=(
            ToolRiskLevel.medium
        ),
        requires_confirmation=False,
        allowed_in_background=True,
    ),
}


def run_financial_fact_extractor(
    user_id: str,
    tool_input: FinancialFactExtractorInput,
) -> dict:
    return (
        financial_fact_extractor_tool(
            user_id=user_id,
            tool_input=tool_input,
        )
        .model_dump(
            mode="json"
        )
    )

def list_tool_definitions() -> list[ToolDefinition]:
    return list(TOOL_REGISTRY.values())


def run_memory_lookup(
    user_id: str,
) -> dict:
    return memory_lookup_tool(
        user_id
    )


def run_financial_calculator(
    tool_input: FinancialCalculatorInput,
) -> dict:
    return financial_calculator_tool(
        tool_input
    ).model_dump(
        mode="json"
    )


def run_audit_log(
    user_id: str,
    request_id: str,
    tool_input: AuditLogInput,
) -> dict:
    return audit_log_tool(
        user_id,
        request_id,
        tool_input,
    ).model_dump(
        mode="json"
    )


def run_document_search(
    user_id: str,
    tool_input: DocumentSearchInput,
) -> dict:
    return document_search_tool(
        user_id,
        tool_input,
    ).model_dump(
        mode="json"
    )


def run_csv_profile(
    user_id: str,
    tool_input: CsvProfileInput,
) -> dict:
    return profile_csv_dataset(
        dataset_id=tool_input.dataset_id,
        user_id=user_id,
    ).model_dump(
        mode="json"
    )

def run_chart_planner(
    user_id: str,
    tool_input: ChartRequest,
) -> dict:
    return build_chart_spec(
        user_id=user_id,
        request=tool_input,
    ).model_dump(
        mode="json"
    )

def run_web_research(
    user_id: str,
    tool_input: WebResearchInput,
) -> dict:
    return (
        web_research_tool(
            user_id=user_id,
            tool_input=tool_input,
        )
        .model_dump(
            mode="json"
        )
    )