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

    Legacy Phase 3 ExecutionContext scope fields remain supported while
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

def authorize_registered_tool(
    *,
    tool_name: ToolName,
    context: ExecutionContext,
    confirmation_granted: bool = False,
    background_execution: bool = False,
) -> ToolAuthorizationDecision:
    """
    Apply server-owned Tool Registry policy without requiring an Agent identity.

    This is used by trusted non-agent runtimes such as the legacy LangGraph
    workflow. Agent runtimes must use authorize_tool(), which adds the
    Agent Registry boundary on top.
    """

    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=["tool is not registered"],
        )

    permissions = effective_permissions(context)

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


def authorize_tool(
    *,
    agent_name: AgentName,
    tool_name: ToolName,
    context: ExecutionContext,
    confirmation_granted: bool = False,
    background_execution: bool = False,
) -> ToolAuthorizationDecision:
    """
    Deterministically authorize an agent tool invocation.

    This applies two security layers:

    1. Agent Registry policy
       - Is this agent allowed to use this tool?
       - Is this agent allowed network access?
       - Does this agent require web permission?

    2. Tool Registry policy
       - Does the execution context contain required permissions?
       - Is background execution allowed?
       - Is explicit confirmation required?

    Agents and LLMs may propose tool calls, but they cannot grant
    themselves permissions, network access, confirmation, or authority.
    """

    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=["tool is not registered"],
        )

    # ---------------------------------------------------------
    # 1. Agent Registry boundary
    # ---------------------------------------------------------

    if not agent_can_use_tool(
        agent_name,
        tool_name,
    ):
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=[
                "agent is not permitted to use this tool"
            ],
        )

    definition = get_agent_definition(
        agent_name
    )

    # ---------------------------------------------------------
    # 2. Network boundary
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # 3. Agent-specific web permission boundary
    # ---------------------------------------------------------

    permissions = effective_permissions(
        context
    )

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

    # ---------------------------------------------------------
    # 4. Delegate generic Tool Registry policy
    # ---------------------------------------------------------

    return authorize_registered_tool(
        tool_name=tool_name,
        context=context,
        confirmation_granted=confirmation_granted,
        background_execution=background_execution,
    )

def authorize_registered_tool(
    *,
    tool_name: ToolName,
    context: ExecutionContext,
    confirmation_granted: bool = False,
    background_execution: bool = False,
) -> ToolAuthorizationDecision:
    """
    Apply Tool Registry policy without requiring an Agent identity.

    Used by trusted runtimes such as the legacy LangGraph execution path.

    Agent-based runtimes should use authorize_tool(), which applies
    Agent Registry policy first and then delegates here.
    """

    tool = TOOL_REGISTRY.get(tool_name)

    if tool is None:
        return ToolAuthorizationDecision(
            status=ToolAuthorizationStatus.deny,
            tool_name=tool_name,
            reasons=["tool is not registered"],
        )

    permissions = effective_permissions(context)

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