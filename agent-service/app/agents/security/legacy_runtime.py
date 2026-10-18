from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from app.agents.contracts import (
    ExecutionContext,
    ExecutionLimits,
)
from app.agents.security.permissions import (
    ToolAuthorizationDecision,
    ToolAuthorizationStatus,
    authorize_registered_tool,
)
from app.core.config import settings
from app.schemas.tools import ToolName


class LegacyToolAuthorizationError(PermissionError):
    """Raised when the legacy runtime attempts an unauthorized tool action."""


def build_legacy_execution_context(
    state: Mapping[str, Any],
) -> ExecutionContext:
    """
    Convert trusted legacy LangGraph state into the common OwnAgent
    ExecutionContext used by the permission engine.
    """

    request_id = str(state.get("request_id") or "").strip()
    user_id = str(state.get("user_id") or "").strip()

    if not request_id:
        raise ValueError(
            "Legacy runtime state requires request_id."
        )

    if not user_id:
        raise ValueError(
            "Legacy runtime state requires user_id."
        )

    raw_permissions = (
        state.get("granted_permissions")
        or ()
    )

    granted_permissions = frozenset(
        str(permission)
        for permission in raw_permissions
        if str(permission).strip()
    )

    return ExecutionContext(
        request_id=request_id,
        user_id=user_id,
        tenant_id=state.get("tenant_id"),
        trace_id=state.get("trace_id"),
        provider_id=state.get("provider_id"),

        granted_permissions=granted_permissions,

        use_documents=bool(
            state.get("use_documents", False)
        ),
        document_ids=list(
            state.get("document_ids") or []
        ),
        top_k=int(
            state.get("top_k") or 6
        ),
        dataset_id=state.get("dataset_id"),
        allow_web_fallback=bool(
            state.get("allow_web_fallback", False)
        ),
        trusted_web_domains=list(
            state.get("trusted_web_domains") or []
        ),

        limits=ExecutionLimits(
            max_agent_count=int(
                settings.multi_agent_max_agents_per_request
            ),
            max_coordinator_rounds=int(
                settings.multi_agent_max_coordinator_rounds
            ),
            max_retries_per_agent=int(
                settings.multi_agent_max_retries_per_agent
            ),
            max_graph_depth=int(
                settings.multi_agent_max_graph_depth
            ),
            max_web_searches=int(
                settings.multi_agent_max_web_searches
            ),
            max_web_fetches=int(
                settings.multi_agent_max_web_fetches
            ),
            request_timeout_seconds=float(
                settings.multi_agent_request_timeout_seconds
            ),
            max_concurrency=int(
                settings.multi_agent_max_concurrency
            ),
            max_llm_tokens=int(
                settings.multi_agent_max_llm_tokens
            ),
            max_estimated_cost_usd=float(
                settings.multi_agent_max_estimated_cost_usd
            ),
        ),

        metadata={
            "runtime": "legacy_langgraph",
        },
    )


def authorize_legacy_tool(
    *,
    tool_name: ToolName,
    context: ExecutionContext,
    confirmation_granted: bool = False,
    background_execution: bool = False,
) -> ToolAuthorizationDecision:
    """
    Apply the common lower-level Tool Registry policy to the legacy runtime.
    """

    return authorize_registered_tool(
        tool_name=tool_name,
        context=context,
        confirmation_granted=confirmation_granted,
        background_execution=background_execution,
    )


def require_legacy_tool_authorization(
    *,
    tool_name: ToolName,
    context: ExecutionContext,
    confirmation_granted: bool = False,
    background_execution: bool = False,
) -> None:
    """
    Fail closed before the underlying tool is invoked.
    """

    decision = authorize_legacy_tool(
        tool_name=tool_name,
        context=context,
        confirmation_granted=confirmation_granted,
        background_execution=background_execution,
    )

    if decision.status == ToolAuthorizationStatus.allow:
        return

    reason = (
        "; ".join(decision.reasons)
        or "tool authorization failed"
    )

    if decision.status == ToolAuthorizationStatus.ask:
        raise LegacyToolAuthorizationError(
            f"TOOL_APPROVAL_REQUIRED: "
            f"{tool_name.value}: {reason}"
        )

    raise LegacyToolAuthorizationError(
        f"TOOL_POLICY_DENIED: "
        f"{tool_name.value}: {reason}"
    )