from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import AgentResult, CoordinatorPlan


class MultiAgentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MultiAgentExecutionSummary(MultiAgentSchema):
    """Browser-safe shell reserved for future 3I runtime integration.

    3I-A defines this schema but does not yet add it to /agents/analyze.
    """

    multi_agent_used: bool = False
    plan: CoordinatorPlan | None = None
    results: list[AgentResult] = Field(default_factory=list)
    completed_task_count: int = Field(default=0, ge=0)
    failed_task_count: int = Field(default=0, ge=0)
    partial_task_count: int = Field(default=0, ge=0)
    total_latency_ms: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
