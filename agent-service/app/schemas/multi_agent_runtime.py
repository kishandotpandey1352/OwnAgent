from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.agents.composition.models import ComposedAnswer
from app.agents.observability.models import TraceSummary
from app.agents.review.models import EvidenceReviewSummary
from app.agents.runtime.models import DAGExecutionResult
from app.agents.security.budgets import BudgetDecision
from app.agents.contracts import CoordinatorPlan
from app.governance.compliance import ComplianceReport
from app.versioning import ExecutionVersionManifest


class RuntimeSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MultiAgentAnalyzeRequest(RuntimeSchema):
    question: str = Field(min_length=1, max_length=20_000)
    user_id: str | None = Field(default=None, max_length=200)
    tenant_id: str | None = Field(default=None, max_length=200)
    provider_id: str | None = Field(default=None, max_length=200)
    use_documents: bool = False
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    top_k: int = Field(default=6, ge=1, le=20)
    dataset_id: str | None = Field(default=None, max_length=200)
    allow_web_fallback: bool = False
    trusted_web_domains: list[str] = Field(default_factory=list, max_length=25)
    metadata: dict[str, Any] = Field(default_factory=dict, max_length=25)


class MultiAgentAnalyzeResponse(RuntimeSchema):
    ok: bool = True
    request_id: str
    trace_id: str
    answer: ComposedAnswer
    plan: CoordinatorPlan
    execution: DAGExecutionResult
    review: EvidenceReviewSummary
    compliance: ComplianceReport
    pre_execution_budget: BudgetDecision
    post_execution_budget: BudgetDecision
    trace: TraceSummary
    version_manifest: ExecutionVersionManifest
