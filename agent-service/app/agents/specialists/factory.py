from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from app.agents.contracts import AgentName
from app.agents.specialists.base import SpecialistAgent
from app.agents.specialists.calculation import CalculationAgent
from app.agents.specialists.chart import ChartAgent
from app.agents.specialists.data_analysis import DataAnalysisAgent
from app.agents.specialists.document import DocumentAgent
from app.agents.specialists.financial_fact import FinancialFactAgent
from app.agents.specialists.web_research import WebResearchAgent


_SPECIALIST_AGENTS: dict[AgentName, SpecialistAgent] = {
    AgentName.document_agent: DocumentAgent(),
    AgentName.web_research_agent: WebResearchAgent(),
    AgentName.financial_fact_agent: FinancialFactAgent(),
    AgentName.data_analysis_agent: DataAnalysisAgent(),
    AgentName.calculation_agent: CalculationAgent(),
    AgentName.chart_agent: ChartAgent(),
}

SPECIALIST_AGENTS: Mapping[AgentName, SpecialistAgent] = MappingProxyType(
    _SPECIALIST_AGENTS
)


def get_specialist_agent(agent_name: AgentName) -> SpecialistAgent:
    try:
        return SPECIALIST_AGENTS[agent_name]
    except KeyError as exc:
        raise ValueError(
            f"Agent {agent_name.value!r} does not have a 3I-B specialist wrapper."
        ) from exc
