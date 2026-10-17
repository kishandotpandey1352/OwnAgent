from app.agents.contracts import (
    AgentName,
    ExecutionContext,
    ExecutionLimits,
)
from app.agents.security.permissions import (
    ToolAuthorizationStatus,
    authorize_tool,
)
from app.schemas.tools import ToolName


def make_context(
    permissions: frozenset[str] = frozenset(),
) -> ExecutionContext:
    return ExecutionContext(
        request_id="req-test",
        user_id="user-test",
        granted_permissions=permissions,
        limits=ExecutionLimits(
            max_agent_count=8,
            max_coordinator_rounds=2,
            max_retries_per_agent=1,
            max_graph_depth=8,
            max_web_searches=5,
            max_web_fetches=10,
            request_timeout_seconds=60,
            max_concurrency=4,
            max_llm_tokens=100_000,
            max_estimated_cost_usd=5.0,
        ),
    )


def test_document_agent_requires_document_permission():
    context = make_context()

    decision = authorize_tool(
        agent_name=AgentName.document_agent,
        tool_name=ToolName.document_search,
        context=context,
    )

    assert decision.status == ToolAuthorizationStatus.deny
    assert decision.allowed is False


def test_document_agent_allowed_with_document_permission():
    context = make_context(
        frozenset({"documents.read"})
    )

    decision = authorize_tool(
        agent_name=AgentName.document_agent,
        tool_name=ToolName.document_search,
        context=context,
    )

    assert decision.status == ToolAuthorizationStatus.allow
    assert decision.allowed is True


def test_agent_cannot_use_tool_outside_registry():
    context = make_context(
        frozenset({"documents.read"})
    )

    decision = authorize_tool(
        agent_name=AgentName.calculation_agent,
        tool_name=ToolName.document_search,
        context=context,
    )

    assert decision.status == ToolAuthorizationStatus.deny


def test_web_research_requires_web_permission():
    context = make_context()

    decision = authorize_tool(
        agent_name=AgentName.web_research_agent,
        tool_name=ToolName.web_research,
        context=context,
    )

    assert decision.status == ToolAuthorizationStatus.deny


def test_web_research_allowed_with_permission():
    context = make_context(
        frozenset({"web.search"})
    )

    decision = authorize_tool(
        agent_name=AgentName.web_research_agent,
        tool_name=ToolName.web_research,
        context=context,
    )

    assert decision.status == ToolAuthorizationStatus.allow


def test_financial_calculator_requires_no_user_permission():
    context = make_context()

    decision = authorize_tool(
        agent_name=AgentName.calculation_agent,
        tool_name=ToolName.financial_calculator,
        context=context,
    )

    assert decision.status == ToolAuthorizationStatus.allow


def test_legacy_document_scope_grants_document_read():
    context = make_context().model_copy(
        update={"use_documents": True}
    )

    decision = authorize_tool(
        agent_name=AgentName.document_agent,
        tool_name=ToolName.document_search,
        context=context,
    )

    assert decision.status == ToolAuthorizationStatus.allow


def test_legacy_web_scope_grants_web_search():
    context = make_context().model_copy(
        update={"allow_web_fallback": True}
    )

    decision = authorize_tool(
        agent_name=AgentName.web_research_agent,
        tool_name=ToolName.web_research,
        context=context,
    )

    assert decision.status == ToolAuthorizationStatus.allow