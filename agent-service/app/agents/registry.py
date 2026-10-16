from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import (
    AgentCapability,
    AgentName,
    NetworkAccess,
)
from app.core.config import settings
from app.schemas.tools import ToolName
from app.tools.registry import TOOL_REGISTRY


class AgentDefinition(BaseModel):
    """Server-owned least-privilege policy for a registered agent."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    name: AgentName
    version: str = Field(default="1.0.0", min_length=1, max_length=50)
    capabilities: frozenset[AgentCapability]
    allowed_tools: frozenset[ToolName] = Field(default_factory=frozenset)

    network_access: NetworkAccess = NetworkAccess.none
    document_access: bool = False
    dataset_access: bool = False
    llm_required: bool = False
    web_permission_required: bool = False

    # Agents may never recursively invent/delegate to other agents.
    can_call_agents: bool = False

    timeout_seconds: float = Field(gt=0.0, le=300.0)
    retry_limit: int = Field(ge=0, le=3)
    estimated_cost_limit_usd: float = Field(ge=0.0, le=100.0)


def _definition(
    *,
    name: AgentName,
    capabilities: set[AgentCapability],
    allowed_tools: set[ToolName] | None = None,
    network_access: NetworkAccess = NetworkAccess.none,
    document_access: bool = False,
    dataset_access: bool = False,
    llm_required: bool = False,
    web_permission_required: bool = False,
    timeout_seconds: float,
    estimated_cost_limit_usd: float,
) -> AgentDefinition:
    return AgentDefinition(
        name=name,
        capabilities=frozenset(capabilities),
        allowed_tools=frozenset(allowed_tools or set()),
        network_access=network_access,
        document_access=document_access,
        dataset_access=dataset_access,
        llm_required=llm_required,
        web_permission_required=web_permission_required,
        can_call_agents=False,
        timeout_seconds=timeout_seconds,
        retry_limit=int(settings.multi_agent_max_retries_per_agent),
        estimated_cost_limit_usd=estimated_cost_limit_usd,
    )


def _build_registry() -> dict[AgentName, AgentDefinition]:
    default_timeout = float(settings.multi_agent_default_agent_timeout_seconds)

    registry = {
        AgentName.document_agent: _definition(
            name=AgentName.document_agent,
            capabilities={AgentCapability.document_search},
            allowed_tools={ToolName.document_search},
            document_access=True,
            timeout_seconds=default_timeout,
            estimated_cost_limit_usd=float(
                settings.multi_agent_default_agent_cost_limit_usd
            ),
        ),
        AgentName.web_research_agent: _definition(
            name=AgentName.web_research_agent,
            capabilities={AgentCapability.web_research},
            allowed_tools={ToolName.web_research},
            network_access=NetworkAccess.restricted_public_web,
            llm_required=True,
            web_permission_required=True,
            timeout_seconds=float(settings.multi_agent_web_agent_timeout_seconds),
            estimated_cost_limit_usd=float(
                settings.multi_agent_web_agent_cost_limit_usd
            ),
        ),
        AgentName.financial_fact_agent: _definition(
            name=AgentName.financial_fact_agent,
            capabilities={AgentCapability.financial_fact_extraction},
            allowed_tools={ToolName.financial_fact_extractor},
            document_access=True,
            llm_required=True,
            timeout_seconds=default_timeout,
            estimated_cost_limit_usd=float(
                settings.multi_agent_llm_agent_cost_limit_usd
            ),
        ),
        AgentName.data_analysis_agent: _definition(
            name=AgentName.data_analysis_agent,
            capabilities={AgentCapability.data_analysis},
            allowed_tools={ToolName.csv_profile},
            dataset_access=True,
            timeout_seconds=default_timeout,
            estimated_cost_limit_usd=float(
                settings.multi_agent_default_agent_cost_limit_usd
            ),
        ),
        AgentName.calculation_agent: _definition(
            name=AgentName.calculation_agent,
            capabilities={AgentCapability.deterministic_calculation},
            allowed_tools={ToolName.financial_calculator},
            timeout_seconds=min(default_timeout, 10.0),
            estimated_cost_limit_usd=0.0,
        ),
        AgentName.chart_agent: _definition(
            name=AgentName.chart_agent,
            capabilities={AgentCapability.chart_planning},
            allowed_tools={ToolName.chart_planner},
            dataset_access=True,
            timeout_seconds=default_timeout,
            estimated_cost_limit_usd=float(
                settings.multi_agent_default_agent_cost_limit_usd
            ),
        ),
        AgentName.evidence_review_agent: _definition(
            name=AgentName.evidence_review_agent,
            capabilities={AgentCapability.evidence_review},
            llm_required=True,
            timeout_seconds=default_timeout,
            estimated_cost_limit_usd=float(
                settings.multi_agent_llm_agent_cost_limit_usd
            ),
        ),
        AgentName.answer_composer: _definition(
            name=AgentName.answer_composer,
            capabilities={AgentCapability.answer_composition},
            llm_required=True,
            timeout_seconds=default_timeout,
            estimated_cost_limit_usd=float(
                settings.multi_agent_llm_agent_cost_limit_usd
            ),
        ),
    }
    validate_agent_registry(registry)
    return registry


def validate_agent_registry(
    registry: Mapping[AgentName, AgentDefinition],
) -> None:
    expected_agents = set(AgentName)
    registered_agents = set(registry)
    if registered_agents != expected_agents:
        missing = expected_agents - registered_agents
        extra = registered_agents - expected_agents
        raise RuntimeError(
            "Agent registry does not match AgentName. "
            f"missing={sorted(item.value for item in missing)} "
            f"extra={sorted(item.value for item in extra)}"
        )

    known_tools = set(TOOL_REGISTRY)
    for agent_name, definition in registry.items():
        if agent_name != definition.name:
            raise RuntimeError(
                f"Agent registry key {agent_name.value!r} does not match "
                f"definition name {definition.name.value!r}."
            )

        unknown_tools = set(definition.allowed_tools) - known_tools
        if unknown_tools:
            raise RuntimeError(
                f"Agent {agent_name.value!r} references unknown tools: "
                f"{sorted(tool.value for tool in unknown_tools)}"
            )

        if definition.can_call_agents:
            raise RuntimeError(
                f"Agent {agent_name.value!r} may not call other agents."
            )

        if (
            definition.network_access != NetworkAccess.none
            and agent_name != AgentName.web_research_agent
        ):
            raise RuntimeError(
                "Only web_research_agent may receive network access in 3I."
            )

        if definition.web_permission_required and (
            agent_name != AgentName.web_research_agent
        ):
            raise RuntimeError(
                "Only web_research_agent may require web permission."
            )


_AGENT_REGISTRY = _build_registry()
AGENT_REGISTRY: Mapping[AgentName, AgentDefinition] = MappingProxyType(
    _AGENT_REGISTRY
)


def get_agent_definition(agent_name: AgentName) -> AgentDefinition:
    try:
        return AGENT_REGISTRY[agent_name]
    except KeyError as exc:  # defensive if callers bypass enum validation
        raise ValueError(f"Agent is not registered: {agent_name}") from exc


def is_registered_agent(agent_name: AgentName) -> bool:
    return agent_name in AGENT_REGISTRY


def list_agent_definitions() -> list[AgentDefinition]:
    return list(AGENT_REGISTRY.values())


def agent_can_use_tool(agent_name: AgentName, tool_name: ToolName) -> bool:
    definition = get_agent_definition(agent_name)
    return tool_name in definition.allowed_tools
