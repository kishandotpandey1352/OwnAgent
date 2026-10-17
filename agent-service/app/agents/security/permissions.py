from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import (
    AgentName,
    ExecutionContext,
    NetworkAccess,
)
from app.agents.registry import (
    agent_can_use_tool,
    get_agent_definition,
)
from app.schemas.tools import ToolName
from app.tools.registry import TOOL_REGISTRY


class ToolAuthorizationStatus(str, Enum):
    allow = "allow"
    ask = "ask"
    deny = "deny"


class ToolAuthorizationDecision(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    schema_version: str = "ToolAuthorizationDecision.v1"

    status: ToolAuthorizationStatus
    tool_name: ToolName

    reasons: list[str] = Field(
        default_factory=list,
        max_length=25,
    )

    @property
    def allowed(self) -> bool:
        return self.status == ToolAuthorizationStatus.allow


def effective_permissions(
    context: ExecutionContext,
) -> frozenset[str]:
    """
    Resolve permissions already trusted by the runtime.

    Legacy ExecutionContext scope fields remain authoritative while
    OwnAgent migrates toward explicit generic permissions.
    """

    permissions = set(context.granted_permissions)

    if context.use_documents:
        permissions.add("documents.read")

    if context.dataset_id:
        permissions.add("datasets.read")

    if context.allow_web_fallback:
        permissions.add("web.search")

    return frozenset(permissions)


def authorize_tool(
    *,
    agent_name: AgentName,
    tool_name: ToolName,
    context: ExecutionContext,
    confirmation_granted: bool = False,
    background_execution: bool = False,
) -> ToolAuthorizationDecision:
    """
    Authorize an agent tool invocation deterministically.

    Agents and LLMs may propose tool calls but cannot grant themselves
    permissions, confirmations, network access, or background authority.
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
            reasons=[
                "agent is not permitted to use this tool"
            ],
        )

    definition = get_agent_definition(agent_name)

    if (
        tool.network_access
        and definition.network_access == NetworkAccess.none
    ):
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=[
                "agent is not permitted network access"
            ],
        )

    permissions = effective_permissions(context)

    if (
        definition.web_permission_required
        and "web.search" not in permissions
    ):
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=[
                "web access is not permitted for this request"
            ],
        )

    missing_permissions = (
        set(tool.required_permissions)
        - set(permissions)
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

    if (
        background_execution
        and not tool.allowed_in_background
    ):
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=[
                "tool is not permitted during background execution"
            ],
        )

    if (
        tool.requires_confirmation
        and not confirmation_granted
    ):
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.ask,
            tool_name=tool_name,
            reasons=[
                "explicit user confirmation is required"
            ],
        )

    return ToolAuthorizationDecision(
        status=ToolAuthorizationStatus.allow,
        tool_name=tool_name,
    )