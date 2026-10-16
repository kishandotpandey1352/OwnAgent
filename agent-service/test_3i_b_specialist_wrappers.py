from __future__ import annotations

from unittest.mock import patch

from app.agents.contracts import (
    AgentName,
    AgentStatus,
    AgentTask,
    ExecutionContext,
    ExecutionLimits,
)
from app.agents.specialist_inputs import (
    CalculationAgentInput,
    ChartAgentInput,
    DataAnalysisAgentInput,
    DocumentAgentInput,
    FinancialFactAgentInput,
    WebResearchAgentInput,
)
from app.agents.specialists import (
    CalculationAgent,
    ChartAgent,
    DataAnalysisAgent,
    DocumentAgent,
    FinancialFactAgent,
    WebResearchAgent,
)
from app.agents.specialists.factory import SPECIALIST_AGENTS, get_specialist_agent
from app.schemas.chart import ChartRequest
from app.schemas.tools import FinancialCalculationType, FinancialCalculatorInput


def limits() -> ExecutionLimits:
    return ExecutionLimits(
        max_agent_count=6,
        max_coordinator_rounds=2,
        max_retries_per_agent=1,
        max_graph_depth=4,
        max_web_searches=2,
        max_web_fetches=8,
        request_timeout_seconds=90,
        max_concurrency=3,
        max_llm_tokens=24000,
        max_estimated_cost_usd=0.50,
    )


def context(*, allow_web: bool = True) -> ExecutionContext:
    return ExecutionContext(
        request_id="req-3ib",
        user_id="local-demo-user",
        use_documents=True,
        document_ids=["doc-1"],
        top_k=6,
        dataset_id="dataset-1",
        allow_web_fallback=allow_web,
        trusted_web_domains=["sec.gov"],
        limits=limits(),
    )


def task(agent_name: AgentName, *, input_evidence_ids: list[str] | None = None) -> AgentTask:
    return AgentTask(
        task_id=f"task-{agent_name.value}",
        request_id="req-3ib",
        agent_name=agent_name,
        instruction="Execute the bounded specialist task.",
        dependencies=[],
        input_evidence_ids=input_evidence_ids or [],
        required=True,
        timeout_seconds=30,
        retry_limit=1,
        estimated_cost_limit_usd=0.1,
    )


def test_specialist_factory_contains_only_phase_3i_b_wrappers() -> None:
    expected = {
        AgentName.document_agent,
        AgentName.web_research_agent,
        AgentName.financial_fact_agent,
        AgentName.data_analysis_agent,
        AgentName.calculation_agent,
        AgentName.chart_agent,
    }
    assert set(SPECIALIST_AGENTS) == expected
    assert get_specialist_agent(AgentName.document_agent).agent_name == AgentName.document_agent


def test_document_wrapper() -> None:
    payload = {
        "sources": [
            {
                "source_number": 1,
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "file_name": "report.pdf",
                "chunk_index": 2,
                "page_number": 3,
                "score": 0.91,
                "snippet": "Revenue was 100.",
            }
        ],
        "source_count": 1,
        "best_score": 0.91,
        "embedding_model": "text-embedding-3-small",
    }
    with patch("app.agents.specialists.document.run_document_search", return_value=payload):
        result = DocumentAgent().execute(
            task=task(AgentName.document_agent),
            context=context(),
            agent_input=DocumentAgentInput(query="revenue", document_ids=["doc-1"]),
        )
    assert result.status == AgentStatus.completed
    assert len(result.evidence) == 1
    assert result.evidence[0].source.chunk_id == "chunk-1"


def test_web_permission_is_enforced_before_tool_call() -> None:
    with patch("app.agents.specialists.web_research.run_web_research") as mocked:
        result = WebResearchAgent().execute(
            task=task(AgentName.web_research_agent),
            context=context(allow_web=False),
            agent_input=WebResearchAgentInput(query="latest revenue"),
        )
    assert result.status == AgentStatus.failed
    assert result.error is not None
    assert result.error.code == "AGENT_POLICY_DENIED"
    mocked.assert_not_called()


def test_web_wrapper_maps_citation_evidence() -> None:
    payload = {
        "ok": True,
        "provider": "serper",
        "searched": True,
        "evidence_ready": True,
        "citation_ready": True,
        "citation_sources": [
            {
                "source_number": 2001,
                "source_id": "web-source-1",
                "title": "SEC filing",
                "url": "https://www.sec.gov/example",
                "snippet": "Commission income was 103.2 million.",
                "page_number": None,
                "trust_tier": "public_authority",
                "content_type": "html",
                "evidence_score": 0.97,
            }
        ],
        "validated_facts": [],
        "warnings": [],
        "search_cache_hit": False,
        "fetch_cache_hit": False,
    }
    with patch("app.agents.specialists.web_research.run_web_research", return_value=payload):
        result = WebResearchAgent().execute(
            task=task(AgentName.web_research_agent),
            context=context(),
            agent_input=WebResearchAgentInput(query="latest revenue"),
        )
    assert result.status == AgentStatus.completed
    assert result.evidence[0].source.source_number == 2001


def test_financial_fact_wrapper() -> None:
    payload = {
        "ok": True,
        "query": "commission income",
        "document_summaries": [],
        "facts": [
            {
                "fact_id": "fact-1",
                "document_id": "doc-1",
                "source_number": 1,
                "company": "Ambac",
                "metric_key": "commission_income",
                "canonical_metric_key": "commission_income",
                "metric_label": "Commission income",
                "value_type": "currency",
                "numeric_value": "92",
                "normalized_numeric_value": "92000000",
                "text_value": None,
                "raw_value": "$92 million",
                "unit_key": None,
                "unit_label": None,
                "currency": "USD",
                "scale": "unit",
                "period_label": "FY2024",
                "period_start": None,
                "period_end": None,
                "category": None,
                "statement_type": None,
                "validation_score": 0.98,
            }
        ],
        "sources": [
            {
                "source_number": 1,
                "source_ledger_id": "ledger-1",
                "document_id": "doc-1",
                "chunk_id": "chunk-1",
                "source_title": "report.pdf",
                "page_number": 10,
                "source_snippet": "Commission income $92 million",
                "retrieval_score": 0.9,
            }
        ],
        "warnings": [],
    }
    with patch("app.agents.specialists.financial_fact.run_financial_fact_extractor", return_value=payload):
        result = FinancialFactAgent().execute(
            task=task(AgentName.financial_fact_agent),
            context=context(),
            agent_input=FinancialFactAgentInput(
                document_ids=["doc-1"],
                query="commission income",
            ),
        )
    assert result.status == AgentStatus.completed
    assert result.evidence[0].metric == "Commission income"
    assert str(result.evidence[0].normalized_numeric_value) == "92000000"


def test_data_wrapper_blocks_cross_dataset_access() -> None:
    with patch("app.agents.specialists.data_analysis.run_csv_profile") as mocked:
        result = DataAnalysisAgent().execute(
            task=task(AgentName.data_analysis_agent),
            context=context(),
            agent_input=DataAnalysisAgentInput(dataset_id="other-dataset"),
        )
    assert result.status == AgentStatus.failed
    assert result.error is not None
    assert result.error.code == "AGENT_POLICY_DENIED"
    mocked.assert_not_called()


def test_calculation_wrapper_has_lineage() -> None:
    with patch(
        "app.agents.specialists.calculation.run_financial_calculator",
        return_value={
            "calculation_type": "growth_rate",
            "result": 0.10,
            "result_percent": 10.0,
            "explanation": "Growth rate = (current value - previous value) / absolute previous value.",
        },
    ):
        result = CalculationAgent().execute(
            task=task(AgentName.calculation_agent),
            context=context(),
            agent_input=CalculationAgentInput(
                calculation=FinancialCalculatorInput(
                    calculation_type=FinancialCalculationType.growth_rate,
                    current_value=110,
                    previous_value=100,
                )
            ),
        )
    assert result.status == AgentStatus.completed
    calc = result.evidence[-1]
    assert calc.calculation_lineage is not None
    assert calc.calculation_lineage.input_evidence_ids


def test_chart_wrapper() -> None:
    payload = {
        "ok": True,
        "dataset_id": "dataset-1",
        "file_name": "sales.csv",
        "chart_type": "line",
        "title": "Revenue by Month",
        "x": "Month",
        "series": ["Revenue"],
        "data": [{"Month": "Jan", "Revenue": 100.0}],
        "source_row_count": 1,
        "chart_row_count": 1,
        "sampled": False,
        "explanation": "Line chart showing revenue by month.",
        "source_coverage": 1.0,
        "warnings": [],
    }
    with patch("app.agents.specialists.chart.run_chart_planner", return_value=payload):
        result = ChartAgent().execute(
            task=task(AgentName.chart_agent),
            context=context(),
            agent_input=ChartAgentInput(
                request=ChartRequest(
                    dataset_id="dataset-1",
                    chart_type="line",
                    x="Month",
                    series=["Revenue"],
                )
            ),
        )
    assert result.status == AgentStatus.completed
    assert result.evidence[0].metadata["chart_spec"]["chart_type"] == "line"


def main() -> None:
    test_specialist_factory_contains_only_phase_3i_b_wrappers()
    test_document_wrapper()
    test_web_permission_is_enforced_before_tool_call()
    test_web_wrapper_maps_citation_evidence()
    test_financial_fact_wrapper()
    test_data_wrapper_blocks_cross_dataset_access()
    test_calculation_wrapper_has_lineage()
    test_chart_wrapper()
    print("PASS: 3I-B specialist wrappers are bounded and evidence-producing.")


if __name__ == "__main__":
    main()
