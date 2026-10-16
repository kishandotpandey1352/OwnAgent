from enum import Enum
from typing import Any

from pydantic import BaseModel, Field
from app.schemas.chart import ChartRequest
from datetime import date
from decimal import Decimal

class ToolRiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ToolName(str, Enum):
    memory_lookup = "memory_lookup"
    financial_calculator = "financial_calculator"
    audit_log = "audit_log"
    document_search = "document_search"

    # Phase 3E
    csv_profile = "csv_profile"
    # Phase 3F
    chart_planner = "chart_planner"
    financial_fact_extractor = ("financial_fact_extractor")
    web_research = "web_research"


class ToolCallStatus(str, Enum):
    planned = "planned"
    completed = "completed"
    skipped = "skipped"
    failed = "failed"


class ToolDefinition(BaseModel):
    name: ToolName
    description: str
    risk_level: ToolRiskLevel
    requires_confirmation: bool = False
    allowed_in_background: bool = True


class ToolCallRecord(BaseModel):
    tool_name: ToolName
    status: ToolCallStatus
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


# ---------------------------------------------------------
# Financial calculator
# ---------------------------------------------------------


class FinancialCalculationType(str, Enum):
    growth_rate = "growth_rate"
    margin = "margin"
    delta = "delta"
    percentage_of = "percentage_of"
    cagr = "cagr"


class FinancialCalculatorInput(BaseModel):
    calculation_type: FinancialCalculationType

    current_value: float | None = None
    previous_value: float | None = None

    numerator: float | None = None
    denominator: float | None = None

    beginning_value: float | None = None
    ending_value: float | None = None
    periods: float | None = None


class FinancialCalculatorOutput(BaseModel):
    calculation_type: FinancialCalculationType
    result: float
    result_percent: float | None = None
    explanation: str


# ---------------------------------------------------------
# Audit
# ---------------------------------------------------------


class AuditLogInput(BaseModel):
    event_type: str
    agent_name: str = "finance_memory_agent"
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditLogOutput(BaseModel):
    ok: bool
    event_id: str
    event_type: str


# ---------------------------------------------------------
# Document search
# ---------------------------------------------------------


class DocumentSearchInput(BaseModel):
    query: str = Field(min_length=1)
    document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=6, ge=1, le=20)


class DocumentSource(BaseModel):
    source_number: int
    document_id: str
    chunk_id: str
    file_name: str
    chunk_index: int
    page_number: int | None = None
    score: float
    snippet: str


class DocumentSearchOutput(BaseModel):
    sources: list[DocumentSource] = Field(default_factory=list)
    source_count: int = 0
    best_score: float = 0.0
    embedding_model: str


# ---------------------------------------------------------
# CSV profile - Phase 3E
# ---------------------------------------------------------


class CsvProfileInput(BaseModel):
    dataset_id: str = Field(min_length=1)



class FinancialFactExtractorInput(
    BaseModel,
):
    document_ids: list[str] = Field(
        min_length=1,
        max_length=3,
    )

    query: str = Field(
        min_length=1,
        max_length=2000,
    )

    requested_metrics: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    max_facts_per_document: int = Field(
        default=60,
        ge=1,
        le=100,
    )

    max_returned_facts: int = Field(
        default=40,
        ge=1,
        le=100,
    )


class FinancialFactToolSource(
    BaseModel,
):
    source_number: int

    source_ledger_id: str

    document_id: str

    chunk_id: str | None = None

    source_title: str | None = None

    page_number: int | None = None

    source_snippet: str

    retrieval_score: float | None = None


class FinancialFactToolFact(
    BaseModel,
):
    fact_id: str

    document_id: str

    source_number: int

    company: str | None = None

    metric_key: str

    canonical_metric_key: (
        str | None
    ) = None

    metric_label: str

    value_type: str

    numeric_value: (
        Decimal | None
    ) = None

    normalized_numeric_value: (
        Decimal | None
    ) = None

    text_value: str | None = None

    raw_value: str

    unit_key: str | None = None

    unit_label: str | None = None

    currency: str | None = None

    scale: str | None = None

    period_label: str | None = None

    period_start: date | None = None

    period_end: date | None = None

    category: str | None = None

    statement_type: str | None = None

    validation_score: (
        float | None
    ) = None


class FinancialFactToolDocumentSummary(
    BaseModel,
):
    document_id: str

    ok: bool = True

    extraction_performed: bool = False

    extracted_count: int = 0

    persisted_count: int = 0

    processed_count: int = 0

    validated_count: int = 0

    rejected_count: int = 0

    conflict_count: int = 0

    error: str | None = None

    warnings: list[str] = Field(
        default_factory=list,
    )


class FinancialFactExtractorOutput(
    BaseModel,
):
    ok: bool = True

    query: str

    document_summaries: list[
        FinancialFactToolDocumentSummary
    ] = Field(
        default_factory=list,
    )

    facts: list[
        FinancialFactToolFact
    ] = Field(
        default_factory=list,
    )

    sources: list[
        FinancialFactToolSource
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )

# ---------------------------------------------------------
# Tool plan
# ---------------------------------------------------------


class ToolPlan(BaseModel):
    use_memory_lookup: bool = True

    use_financial_calculator: bool = False
    financial_calculator_input: FinancialCalculatorInput | None = None

    use_document_search: bool = False
    document_search_input: DocumentSearchInput | None = None

    use_csv_profile: bool = False
    csv_profile_input: CsvProfileInput | None = None

    # Phase 3F
    use_chart_planner: bool = False
    chart_planner_input: ChartRequest | None = None

    use_financial_fact_extractor: (bool) = False
    financial_fact_extractor_input: (FinancialFactExtractorInput| None) = None
    use_web_financial_fact_extractor: bool = False

    reason: str