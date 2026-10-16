from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from time import perf_counter

from app.agents.contracts import (
    AgentEvidence,
    AgentName,
    AgentResult,
    AgentStatus,
    AgentTask,
    EvidenceSource,
    EvidenceSourceType,
    ExecutionContext,
)
from app.agents.specialist_inputs import WebResearchAgentInput
from app.agents.specialists.base import SpecialistAgent, SpecialistPolicyError
from app.schemas.tools import ToolName
from app.schemas.web import WebResearchInput
from app.tools.registry import run_web_research


class WebResearchAgent(SpecialistAgent):
    agent_name = AgentName.web_research_agent
    tool_name = ToolName.web_research

    def execute(
        self,
        *,
        task: AgentTask,
        context: ExecutionContext,
        agent_input: WebResearchAgentInput,
    ) -> AgentResult:
        def invoke() -> dict:
            if not context.allow_web_fallback:
                raise SpecialistPolicyError("Public web research is not permitted for this request.")

            allowed_domains = set(context.trusted_web_domains)
            requested_domains = set(agent_input.trusted_domains)
            if requested_domains and not requested_domains.issubset(allowed_domains):
                raise SpecialistPolicyError(
                    "Web agent attempted to use trusted domains outside the execution context."
                )

            return run_web_research(
                context.user_id,
                WebResearchInput(
                    query=agent_input.query,
                    gap_reason=agent_input.gap_reason,
                    trusted_domains=agent_input.trusted_domains,
                    max_results=min(agent_input.max_results, context.limits.max_web_fetches),
                    extract_structured_facts=agent_input.extract_structured_facts,
                ),
            )

        def to_result(output: dict, started_at: datetime, started_clock: float) -> AgentResult:
            evidence: list[AgentEvidence] = []
            citation_by_number = {
                item.get("source_number"): item
                for item in output.get("citation_sources", [])
                if item.get("source_number") is not None
            }

            for citation in output.get("citation_sources", []):
                evidence.append(
                    AgentEvidence(
                        evidence_id=f"{task.task_id}:web:{citation['source_number']}",
                        source_agent=self.agent_name,
                        source=EvidenceSource(
                            source_type=EvidenceSourceType.web,
                            source_id=citation["source_id"],
                            source_number=citation["source_number"],
                            title=citation.get("title"),
                            url=citation.get("url"),
                            page_number=citation.get("page_number"),
                        ),
                        confidence=(
                            max(0.0, min(float(citation["evidence_score"]), 1.0))
                            if citation.get("evidence_score") is not None
                            else None
                        ),
                        snippet=citation.get("snippet"),
                        metadata={
                            "trust_tier": citation.get("trust_tier"),
                            "provider": output.get("provider"),
                            "content_type": citation.get("content_type"),
                        },
                    )
                )

            for fact in output.get("validated_facts", []):
                citation = citation_by_number.get(fact.get("source_number"), {})
                numeric = fact.get("normalized_numeric_value")
                if numeric is None:
                    numeric = fact.get("numeric_value")
                evidence.append(
                    AgentEvidence(
                        evidence_id=f"{task.task_id}:webfact:{fact['fact_id']}",
                        source_agent=self.agent_name,
                        source=EvidenceSource(
                            source_type=EvidenceSourceType.web,
                            source_id=fact["source_ledger_id"],
                            source_number=fact["source_number"],
                            title=citation.get("title"),
                            url=citation.get("url"),
                            page_number=citation.get("page_number"),
                        ),
                        entity=fact.get("company"),
                        metric=fact.get("metric_label") or fact.get("canonical_metric_key"),
                        raw_value=fact.get("raw_value"),
                        normalized_numeric_value=(Decimal(str(numeric)) if numeric is not None else None),
                        currency=fact.get("currency"),
                        scale=fact.get("scale"),
                        unit=fact.get("unit_label"),
                        period_label=fact.get("period_label"),
                        confidence=fact.get("validation_score"),
                        metadata={
                            "fact_id": fact.get("fact_id"),
                            "metric_key": fact.get("metric_key"),
                            "canonical_metric_key": fact.get("canonical_metric_key"),
                            "underlying_fact_validated": True,
                        },
                    )
                )

            warnings = [str(item) for item in output.get("warnings", [])]
            status = AgentStatus.completed if output.get("ok", True) else AgentStatus.partial
            return AgentResult(
                task_id=task.task_id,
                request_id=task.request_id,
                agent_name=self.agent_name,
                status=status,
                evidence=evidence,
                warnings=warnings,
                latency_ms=max(0, int((perf_counter() - started_clock) * 1000)),
                token_usage=(int(output["token_usage"]) if output.get("token_usage") is not None else None),
                estimated_cost_usd=(float(output["estimated_cost_usd"]) if output.get("estimated_cost_usd") is not None else None),
                started_at=started_at,
                metadata={
                    "agent_version": self.version,
                    "tool_name": self.tool_name.value,
                    "searched": output.get("searched", False),
                    "evidence_ready": output.get("evidence_ready", False),
                    "citation_ready": output.get("citation_ready", False),
                    "search_cache_hit": output.get("search_cache_hit", False),
                    "fetch_cache_hit": output.get("fetch_cache_hit", False),
                    "web_search_count": int(output.get("search_count", 1 if output.get("searched") else 0) or 0),
                    "web_fetch_count": int(output.get("fetch_count", len(output.get("citation_sources", []))) or 0),
                },
            )

        return self._execute_guarded(
            task=task,
            context=context,
            invoke=invoke,
            to_result=to_result,
        )
