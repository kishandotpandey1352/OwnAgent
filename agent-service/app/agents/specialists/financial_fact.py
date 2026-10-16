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
from app.agents.specialist_inputs import FinancialFactAgentInput
from app.agents.specialists.base import SpecialistAgent, SpecialistPolicyError
from app.schemas.tools import FinancialFactExtractorInput, ToolName
from app.tools.registry import run_financial_fact_extractor


class FinancialFactAgent(SpecialistAgent):
    agent_name = AgentName.financial_fact_agent
    tool_name = ToolName.financial_fact_extractor

    def execute(
        self,
        *,
        task: AgentTask,
        context: ExecutionContext,
        agent_input: FinancialFactAgentInput,
    ) -> AgentResult:
        def invoke() -> dict:
            if not context.use_documents:
                raise SpecialistPolicyError("Document access is disabled for this request.")
            if not set(agent_input.document_ids).issubset(set(context.document_ids)):
                raise SpecialistPolicyError(
                    "Financial fact agent attempted to access a document outside the execution context."
                )
            return run_financial_fact_extractor(
                context.user_id,
                FinancialFactExtractorInput(**agent_input.model_dump()),
            )

        def to_result(output: dict, started_at: datetime, started_clock: float) -> AgentResult:
            sources_by_number = {
                item["source_number"]: item for item in output.get("sources", [])
            }
            evidence: list[AgentEvidence] = []
            for fact in output.get("facts", []):
                source = sources_by_number.get(fact["source_number"], {})
                numeric = fact.get("normalized_numeric_value")
                if numeric is None:
                    numeric = fact.get("numeric_value")
                evidence.append(
                    AgentEvidence(
                        evidence_id=f"{task.task_id}:fact:{fact['fact_id']}",
                        source_agent=self.agent_name,
                        source=EvidenceSource(
                            source_type=EvidenceSourceType.document,
                            source_id=source.get("source_ledger_id", fact["fact_id"]),
                            source_number=fact.get("source_number"),
                            title=source.get("source_title"),
                            document_id=fact.get("document_id"),
                            chunk_id=source.get("chunk_id"),
                            page_number=source.get("page_number"),
                        ),
                        entity=fact.get("company"),
                        metric=fact.get("metric_label") or fact.get("canonical_metric_key"),
                        raw_value=fact.get("raw_value"),
                        normalized_numeric_value=(Decimal(str(numeric)) if numeric is not None else None),
                        currency=fact.get("currency"),
                        scale=fact.get("scale"),
                        unit=fact.get("unit_label"),
                        period_label=fact.get("period_label"),
                        period_start=fact.get("period_start"),
                        period_end=fact.get("period_end"),
                        confidence=fact.get("validation_score"),
                        snippet=source.get("source_snippet"),
                        metadata={
                            "fact_id": fact.get("fact_id"),
                            "metric_key": fact.get("metric_key"),
                            "canonical_metric_key": fact.get("canonical_metric_key"),
                            "value_type": fact.get("value_type"),
                            "underlying_fact_validation_score": fact.get("validation_score"),
                        },
                    )
                )

            warnings = [str(item) for item in output.get("warnings", [])]
            return AgentResult(
                task_id=task.task_id,
                request_id=task.request_id,
                agent_name=self.agent_name,
                status=AgentStatus.completed if output.get("ok", True) else AgentStatus.partial,
                evidence=evidence,
                warnings=warnings,
                latency_ms=max(0, int((perf_counter() - started_clock) * 1000)),
                token_usage=(int(output["token_usage"]) if output.get("token_usage") is not None else None),
                estimated_cost_usd=(float(output["estimated_cost_usd"]) if output.get("estimated_cost_usd") is not None else None),
                started_at=started_at,
                metadata={
                    "agent_version": self.version,
                    "tool_name": self.tool_name.value,
                    "fact_count": len(output.get("facts", [])),
                    "document_summary_count": len(output.get("document_summaries", [])),
                },
            )

        return self._execute_guarded(
            task=task,
            context=context,
            invoke=invoke,
            to_result=to_result,
        )
