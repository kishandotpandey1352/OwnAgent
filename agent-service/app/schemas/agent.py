from typing import Any

from pydantic import BaseModel, Field
from app.schemas.chart import ChartRequest
from app.schemas.web import (
    WebProductResearchSummary,
)

class AgentAnalyzeRequest(BaseModel):
    question: str = Field(min_length=1)
    user_id: str | None = None
    provider_id: str | None = None

    use_documents: bool = False
    document_ids: list[str] = Field(default_factory=list)
    top_k: int = Field(default=6, ge=1, le=20)
    
    # Phase 3E
    dataset_id: str | None = None

    # Phase 3F
    chart_request: ChartRequest | None = None
    allow_web_fallback: bool = False

    trusted_web_domains: list[str] = Field(
        default_factory=list,
        max_length=25,
    )

    metadata: dict[str, Any] = Field(default_factory=dict)
    


class AgentAnalyzeResponse(BaseModel):
    ok: bool
    request_id: str
    answer: str

    memory_context: str
    memory_used_count: int

    model: str

    tool_plan: dict[str, Any] | None = None
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    web_fallback_used: bool = False

    web_fallback_available: bool = False

    web_fallback_reason: str | None = None

    grounding: dict[str, Any] | None = None

    # -----------------------------------------------------
    # Phase 3H-F-A
    # Browser-safe web product response
    # -----------------------------------------------------

    web_research: (
        WebProductResearchSummary
        | None
    ) = None