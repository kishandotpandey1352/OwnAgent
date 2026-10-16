from typing import Any, TypedDict

from app.schemas.tools import ToolCallRecord, ToolPlan
from app.schemas.chart import ChartRequest

class FinanceAgentState(
    TypedDict,
    total=False,
):
    request_id: str
    user_id: str
    question: str
    provider_id: str | None
    metadata: dict[str, Any]

    # Phase 3D
    use_documents: bool
    document_ids: list[str]
    top_k: int

    # Phase 3E
    dataset_id: str | None

    # Phase 3F
    chart_request: ChartRequest | None

    memory_context: str
    memory_used_count: int

    tool_plan: ToolPlan
    tool_results: list[ToolCallRecord]

    answer: str
    model: str

    allow_web_fallback: bool

    trusted_web_domains: list[str]

    web_fallback_used: bool

    web_fallback_available: bool

    web_fallback_reason: str | None

    grounding: dict[str, Any]