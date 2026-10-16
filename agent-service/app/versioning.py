from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExecutionVersionManifest(BaseModel):
    """Versions needed to reproduce historical agent behavior."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = "ExecutionVersionManifest.v1"
    api_version: str
    database_schema_version: str
    agent_contract_version: str
    coordinator_version: str
    workflow_version: str
    compliance_policy_version: str
    event_schema_version: str
    provider_id: str | None = None
    model: str | None = None
    prompt_versions: dict[str, str] = Field(default_factory=dict)
    agent_versions: dict[str, str] = Field(default_factory=dict)
    tool_schema_versions: dict[str, str] = Field(default_factory=dict)


def build_execution_version_manifest(
    *,
    coordinator_version: str,
    workflow_version: str,
    reviewer_version: str,
    composer_version: str,
    provider_id: str | None = None,
    model: str | None = None,
) -> ExecutionVersionManifest:
    """Build the reproducibility manifest stored with governed executions.

    provider_id is intentionally not mislabeled as a model name. If the caller
    knows the concrete model it should pass it explicitly; otherwise model is
    left unset and provider identity can be stored alongside this manifest in
    audit metadata.
    """

    return ExecutionVersionManifest(
        api_version="phase3-api.v1",
        database_schema_version="phase3_001",
        agent_contract_version="AgentTask.v1/AgentEvidence.v1/CoordinatorPlan.v1",
        coordinator_version=coordinator_version,
        workflow_version=workflow_version,
        compliance_policy_version="3J-B.1.0.0",
        event_schema_version="AutomationEvent.v1",
        provider_id=provider_id,
        model=model,
        prompt_versions={},
        agent_versions={
            "specialists": "3I-B.v1",
            "evidence_reviewer": reviewer_version,
            "answer_composer": composer_version,
        },
        tool_schema_versions={},
    )
