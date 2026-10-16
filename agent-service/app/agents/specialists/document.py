from __future__ import annotations

from datetime import datetime
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
from app.agents.specialist_inputs import DocumentAgentInput
from app.agents.specialists.base import SpecialistAgent, SpecialistPolicyError
from app.schemas.tools import DocumentSearchInput, ToolName
from app.tools.registry import run_document_search


class DocumentAgent(SpecialistAgent):
    agent_name = AgentName.document_agent
    tool_name = ToolName.document_search

    def execute(
        self,
        *,
        task: AgentTask,
        context: ExecutionContext,
        agent_input: DocumentAgentInput,
    ) -> AgentResult:
        def invoke() -> dict:
            if not context.use_documents:
                raise SpecialistPolicyError("Document access is disabled for this request.")

            requested_ids = agent_input.document_ids or context.document_ids
            if not requested_ids:
                raise SpecialistPolicyError("No document IDs are available to the document agent.")

            allowed = set(context.document_ids)
            if not set(requested_ids).issubset(allowed):
                raise SpecialistPolicyError(
                    "Document agent attempted to access a document outside the execution context."
                )

            return run_document_search(
                context.user_id,
                DocumentSearchInput(
                    query=agent_input.query,
                    document_ids=requested_ids,
                    top_k=min(agent_input.top_k, context.top_k),
                ),
            )

        def to_result(output: dict, started_at: datetime, started_clock: float) -> AgentResult:
            embedding_model = output.get("embedding_model")
            evidence = [
                AgentEvidence(
                    evidence_id=f"{task.task_id}:doc:{source['source_number']}",
                    source_agent=self.agent_name,
                    source=EvidenceSource(
                        source_type=EvidenceSourceType.document,
                        source_id=source["chunk_id"],
                        source_number=source["source_number"],
                        title=source.get("file_name"),
                        document_id=source["document_id"],
                        chunk_id=source["chunk_id"],
                        page_number=source.get("page_number"),
                    ),
                    confidence=max(0.0, min(float(source.get("score", 0.0)), 1.0)),
                    snippet=source.get("snippet"),
                    metadata={
                        "chunk_index": source.get("chunk_index"),
                        "embedding_model": embedding_model,
                    },
                )
                for source in output.get("sources", [])
            ]
            return AgentResult(
                task_id=task.task_id,
                request_id=task.request_id,
                agent_name=self.agent_name,
                status=AgentStatus.completed,
                evidence=evidence,
                warnings=[],
                latency_ms=max(0, int((perf_counter() - started_clock) * 1000)),
                estimated_cost_usd=0.0,
                started_at=started_at,
                metadata={
                    "agent_version": self.version,
                    "tool_name": self.tool_name.value,
                    "source_count": output.get("source_count", len(evidence)),
                    "best_score": output.get("best_score", 0.0),
                },
            )

        return self._execute_guarded(
            task=task,
            context=context,
            invoke=invoke,
            to_result=to_result,
        )
