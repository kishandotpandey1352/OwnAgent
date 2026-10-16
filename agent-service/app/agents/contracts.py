from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContractModel(BaseModel):
    """Base class for versioned, strict inter-agent contracts."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )


class AgentName(str, Enum):
    document_agent = "document_agent"
    web_research_agent = "web_research_agent"
    financial_fact_agent = "financial_fact_agent"
    data_analysis_agent = "data_analysis_agent"
    calculation_agent = "calculation_agent"
    chart_agent = "chart_agent"
    evidence_review_agent = "evidence_review_agent"
    answer_composer = "answer_composer"


class AgentStatus(str, Enum):
    completed = "completed"
    failed = "failed"
    partial = "partial"
    skipped = "skipped"
    timed_out = "timed_out"


class AgentCapability(str, Enum):
    document_search = "document_search"
    web_research = "web_research"
    financial_fact_extraction = "financial_fact_extraction"
    data_analysis = "data_analysis"
    deterministic_calculation = "deterministic_calculation"
    chart_planning = "chart_planning"
    evidence_review = "evidence_review"
    answer_composition = "answer_composition"


class NetworkAccess(str, Enum):
    none = "none"
    restricted_public_web = "restricted_public_web"


class EvidenceSourceType(str, Enum):
    document = "document"
    web = "web"
    dataset = "dataset"
    calculation = "calculation"
    system = "system"


class EvidenceReviewStatus(str, Enum):
    unreviewed = "unreviewed"
    validated = "validated"
    partial = "partial"
    conflict = "conflict"
    unsupported = "unsupported"
    insufficient = "insufficient"


class AgentError(ContractModel):
    schema_version: Literal["AgentError.v1"] = "AgentError.v1"
    code: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=1000)
    retryable: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=25)


class EvidenceSource(ContractModel):
    schema_version: Literal["EvidenceSource.v1"] = "EvidenceSource.v1"
    source_type: EvidenceSourceType
    source_id: str = Field(min_length=1, max_length=500)
    source_number: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, max_length=500)
    url: str | None = Field(default=None, max_length=2000)
    document_id: str | None = Field(default=None, max_length=200)
    chunk_id: str | None = Field(default=None, max_length=200)
    page_number: int | None = Field(default=None, ge=1)
    retrieved_at: datetime | None = None


class CalculationLineage(ContractModel):
    schema_version: Literal["CalculationLineage.v1"] = "CalculationLineage.v1"
    formula: str = Field(min_length=1, max_length=1000)
    input_evidence_ids: list[str] = Field(
        default_factory=list,
        min_length=1,
        max_length=50,
    )


class AgentEvidence(ContractModel):
    schema_version: Literal["AgentEvidence.v1"] = "AgentEvidence.v1"
    evidence_id: str = Field(min_length=1, max_length=200)
    source_agent: AgentName
    source: EvidenceSource

    entity: str | None = Field(default=None, max_length=300)
    metric: str | None = Field(default=None, max_length=300)
    raw_value: str | None = Field(default=None, max_length=2000)
    normalized_numeric_value: Decimal | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    scale: str | None = Field(default=None, max_length=50)
    unit: str | None = Field(default=None, max_length=100)
    period_label: str | None = Field(default=None, max_length=200)
    period_start: date | None = None
    period_end: date | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    snippet: str | None = Field(default=None, max_length=6000)

    review_status: EvidenceReviewStatus = EvidenceReviewStatus.unreviewed
    calculation_lineage: CalculationLineage | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=50)

    @model_validator(mode="after")
    def validate_source_specific_requirements(self) -> "AgentEvidence":
        if (
            self.source.source_type == EvidenceSourceType.calculation
            and self.calculation_lineage is None
        ):
            raise ValueError(
                "Calculation evidence requires calculation_lineage."
            )
        return self


class AgentTask(ContractModel):
    schema_version: Literal["AgentTask.v1"] = "AgentTask.v1"
    task_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    agent_name: AgentName
    instruction: str = Field(min_length=1, max_length=8000)
    dependencies: list[str] = Field(default_factory=list, max_length=20)
    input_evidence_ids: list[str] = Field(default_factory=list, max_length=50)
    required: bool = True
    timeout_seconds: float = Field(gt=0.0, le=300.0)
    retry_limit: int = Field(ge=0, le=3)
    estimated_cost_limit_usd: float = Field(ge=0.0, le=100.0)
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=25)

    @model_validator(mode="after")
    def validate_dependencies(self) -> "AgentTask":
        if self.task_id in self.dependencies:
            raise ValueError("An agent task cannot depend on itself.")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError("Agent task dependencies must be unique.")
        if len(self.input_evidence_ids) != len(set(self.input_evidence_ids)):
            raise ValueError("Agent task input evidence IDs must be unique.")
        return self


class AgentRequest(ContractModel):
    schema_version: Literal["AgentRequest.v1"] = "AgentRequest.v1"
    request_id: str = Field(min_length=1, max_length=200)
    question: str = Field(min_length=1, max_length=20_000)
    user_id: str = Field(min_length=1, max_length=200)
    tenant_id: str | None = Field(default=None, max_length=200)
    provider_id: str | None = Field(default=None, max_length=200)

    use_documents: bool = False
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    top_k: int = Field(default=6, ge=1, le=20)
    dataset_id: str | None = Field(default=None, max_length=200)
    allow_web_fallback: bool = False
    trusted_web_domains: list[str] = Field(default_factory=list, max_length=25)
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=25)


class AgentResult(ContractModel):
    schema_version: Literal["AgentResult.v1"] = "AgentResult.v1"
    task_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    agent_name: AgentName
    status: AgentStatus
    evidence: list[AgentEvidence] = Field(default_factory=list, max_length=250)
    warnings: list[str] = Field(default_factory=list, max_length=100)
    error: AgentError | None = None
    latency_ms: int = Field(default=0, ge=0)
    token_usage: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)
    started_at: datetime | None = None
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=25)

    @model_validator(mode="after")
    def validate_error_contract(self) -> "AgentResult":
        if self.status in {AgentStatus.failed, AgentStatus.timed_out}:
            if self.error is None:
                raise ValueError(
                    "Failed or timed-out agent results require an AgentError."
                )
        if self.status == AgentStatus.completed and self.error is not None:
            raise ValueError("Completed agent results cannot contain an error.")
        return self


class ExecutionLimits(ContractModel):
    schema_version: Literal["ExecutionLimits.v1"] = "ExecutionLimits.v1"
    max_agent_count: int = Field(ge=1, le=32)
    max_coordinator_rounds: int = Field(ge=1, le=8)
    max_retries_per_agent: int = Field(ge=0, le=3)
    max_graph_depth: int = Field(ge=1, le=16)
    max_web_searches: int = Field(ge=0, le=20)
    max_web_fetches: int = Field(ge=0, le=100)
    request_timeout_seconds: float = Field(gt=0.0, le=600.0)
    max_concurrency: int = Field(ge=1, le=32)
    max_llm_tokens: int = Field(ge=1, le=1_000_000)
    max_estimated_cost_usd: float = Field(ge=0.0, le=1000.0)


class ExecutionContext(ContractModel):
    schema_version: Literal["ExecutionContext.v1"] = "ExecutionContext.v1"
    request_id: str = Field(min_length=1, max_length=200)
    user_id: str = Field(min_length=1, max_length=200)
    tenant_id: str | None = Field(default=None, max_length=200)
    trace_id: str | None = Field(default=None, max_length=200)
    provider_id: str | None = Field(default=None, max_length=200)

    use_documents: bool = False
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    top_k: int = Field(default=6, ge=1, le=20)
    dataset_id: str | None = Field(default=None, max_length=200)
    allow_web_fallback: bool = False
    trusted_web_domains: list[str] = Field(default_factory=list, max_length=25)
    limits: ExecutionLimits
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=25)


class CoordinatorPlan(ContractModel):
    schema_version: Literal["CoordinatorPlan.v1"] = "CoordinatorPlan.v1"
    plan_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(min_length=1, max_length=200)
    tasks: list[AgentTask] = Field(min_length=1, max_length=32)
    coordinator_version: str = Field(min_length=1, max_length=100)
    estimated_cost_limit_usd: float = Field(ge=0.0, le=1000.0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=25)

    @model_validator(mode="after")
    def validate_task_references(self) -> "CoordinatorPlan":
        task_ids = [task.task_id for task in self.tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("CoordinatorPlan task IDs must be unique.")

        task_id_set = set(task_ids)
        for task in self.tasks:
            unknown = set(task.dependencies) - task_id_set
            if unknown:
                raise ValueError(
                    f"Task {task.task_id!r} contains unknown dependencies: "
                    f"{sorted(unknown)}"
                )
            if task.request_id != self.request_id:
                raise ValueError(
                    f"Task {task.task_id!r} request_id does not match plan."
                )
        return self
