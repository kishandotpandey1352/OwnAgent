from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import AgentName, ExecutionContext
from app.agents.registry import agent_can_use_tool
from app.schemas.tools import ToolName
from app.tools.registry import TOOL_REGISTRY


class ToolAuthorizationStatus(str, Enum):
    allow = "allow"
    ask = "ask"
    deny = "deny"


class ToolAuthorizationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "ToolAuthorizationDecision.v1"

    status: ToolAuthorizationStatus
    tool_name: ToolName

    reasons: list[str] = Field(default_factory=list, max_length=25)

    @property
    def allowed(self) -> bool:
        return self.status == ToolAuthorizationStatus.allow


def authorize_tool(
    *,
    agent_name: AgentName,
    tool_name: ToolName,
    context: ExecutionContext,
    confirmation_granted: bool = False,
    background_execution: bool = False,
) -> ToolAuthorizationDecision:
    """
    Deterministically authorize a tool execution.

    The LLM or agent may propose a tool call, but cannot grant itself
    permissions, confirmation, or background execution authority.
    """

    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=["tool is not registered"],
        )

    if not agent_can_use_tool(agent_name, tool_name):
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=["agent is not permitted to use this tool"],
        )

    missing_permissions = (
        set(tool.required_permissions)
        - set(context.granted_permissions)
    )

    if missing_permissions:
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=[
                "missing permissions: "
                + ", ".join(sorted(missing_permissions))
            ],
        )

    if background_execution and not tool.allowed_in_background:
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=["tool is not permitted during background execution"],
        )

    if tool.requires_confirmation and not confirmation_granted:
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.ask,
            tool_name=tool_name,
            reasons=["explicit user confirmation is required"],
        )

    return ToolAuthorizationDecision(
        status=ToolAuthorizationStatus.allow,
        tool_name=tool_name,
    )