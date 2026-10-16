from app.agents.contracts import AgentName, NetworkAccess
from app.agents.registry import (
    AGENT_REGISTRY,
    agent_can_use_tool,
    get_agent_definition,
    validate_agent_registry,
)
from app.schemas.tools import ToolName


def test_all_expected_agents_are_registered() -> None:
    assert set(AGENT_REGISTRY) == set(AgentName)
    validate_agent_registry(AGENT_REGISTRY)


def test_document_agent_is_least_privilege() -> None:
    definition = get_agent_definition(AgentName.document_agent)
    assert definition.network_access == NetworkAccess.none
    assert definition.document_access is True
    assert agent_can_use_tool(
        AgentName.document_agent,
        ToolName.document_search,
    )
    assert not agent_can_use_tool(
        AgentName.document_agent,
        ToolName.web_research,
    )


def test_web_agent_requires_explicit_web_permission() -> None:
    definition = get_agent_definition(AgentName.web_research_agent)
    assert definition.network_access == NetworkAccess.restricted_public_web
    assert definition.web_permission_required is True
    assert definition.allowed_tools == frozenset({ToolName.web_research})


def test_calculation_agent_is_deterministic() -> None:
    definition = get_agent_definition(AgentName.calculation_agent)
    assert definition.llm_required is False
    assert definition.network_access == NetworkAccess.none
    assert definition.estimated_cost_limit_usd == 0.0
    assert definition.allowed_tools == frozenset({ToolName.financial_calculator})


def test_reviewer_and_composer_have_no_tools() -> None:
    reviewer = get_agent_definition(AgentName.evidence_review_agent)
    composer = get_agent_definition(AgentName.answer_composer)

    assert reviewer.allowed_tools == frozenset()
    assert composer.allowed_tools == frozenset()
    assert reviewer.network_access == NetworkAccess.none
    assert composer.network_access == NetworkAccess.none
    assert reviewer.can_call_agents is False
    assert composer.can_call_agents is False


def main() -> None:
    test_all_expected_agents_are_registered()
    test_document_agent_is_least_privilege()
    test_web_agent_requires_explicit_web_permission()
    test_calculation_agent_is_deterministic()
    test_reviewer_and_composer_have_no_tools()
    print("PASS: 3I-A least-privilege agent registry validated.")


if __name__ == "__main__":
    main()
