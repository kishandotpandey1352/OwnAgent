from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.agents.contracts import AgentRequest, ExecutionContext
from app.agents.pipeline import MultiAgentPipeline, MultiAgentPipelineResult
from app.governance.audit import AuditActorType, AuditSeverity, InMemoryAuditStore
from app.governance.compliance import ComplianceReport, evaluate_compliance
from app.versioning import ExecutionVersionManifest, build_execution_version_manifest


class GovernedRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "GovernedRunResult.v1"
    pipeline: MultiAgentPipelineResult
    compliance: ComplianceReport
    version_manifest: ExecutionVersionManifest


class GovernedMultiAgentPipeline:
    """Bridge from Phase 3I execution into Phase 3J governance."""

    def __init__(
        self,
        *,
        pipeline: MultiAgentPipeline | None = None,
        audit_store: InMemoryAuditStore | None = None,
    ) -> None:
        self.pipeline = pipeline or MultiAgentPipeline()
        self.audit_store = audit_store or InMemoryAuditStore()

    async def run(
        self,
        *,
        request: AgentRequest,
        context: ExecutionContext,
    ) -> GovernedRunResult:
        self.audit_store.emit(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            trace_id=context.trace_id,
            event_type="request.received",
            actor_type=AuditActorType.user,
            actor_id=request.user_id,
            metadata={"question_length": len(request.question)},
        )

        try:
            pipeline_result = await self.pipeline.run(request=request, context=context)
        except Exception as exc:
            self.audit_store.emit(
                request_id=request.request_id,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                trace_id=context.trace_id,
                event_type="request.failed",
                actor_type=AuditActorType.system,
                actor_id="multi-agent-runtime",
                severity=AuditSeverity.error,
                metadata={"error_type": type(exc).__name__},
            )
            raise

        version_manifest = build_execution_version_manifest(
            coordinator_version=pipeline_result.plan.coordinator_version,
            workflow_version=self.pipeline.version,
            reviewer_version=self.pipeline.reviewer.version,
            composer_version=self.pipeline.composer.version,
            provider_id=context.provider_id,
            model=str(context.metadata.get("model")) if context.metadata.get("model") else None,
        )

        self.audit_store.emit(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            trace_id=context.trace_id,
            plan_id=pipeline_result.plan.plan_id,
            event_type="plan.created",
            actor_type=AuditActorType.system,
            actor_id="coordinator",
            metadata={"task_count": len(pipeline_result.plan.tasks), "provider_id": context.provider_id, "versions": version_manifest.model_dump(mode="json")},
        )
        for result in pipeline_result.execution.results:
            self.audit_store.emit(
                request_id=request.request_id,
                tenant_id=request.tenant_id,
                user_id=request.user_id,
                trace_id=context.trace_id,
                plan_id=pipeline_result.plan.plan_id,
                task_id=result.task_id,
                event_type=(
                    "agent.completed"
                    if result.status.value in {"completed", "partial"}
                    else "agent.failed"
                ),
                actor_type=AuditActorType.agent,
                actor_id=result.agent_name.value,
                severity=(
                    AuditSeverity.info
                    if result.status.value in {"completed", "partial", "skipped"}
                    else AuditSeverity.error
                ),
                metadata={
                    "status": result.status.value,
                    "latency_ms": result.latency_ms,
                    "token_usage": result.token_usage,
                    "estimated_cost_usd": result.estimated_cost_usd,
                    "error_code": result.error.code if result.error else None,
                },
            )

        compliance = evaluate_compliance(
            context=context,
            review=pipeline_result.review,
            answer=pipeline_result.answer,
            agent_results=pipeline_result.execution.results,
            budget_decision=pipeline_result.post_execution_budget,
        )
        self.audit_store.emit(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            trace_id=context.trace_id,
            plan_id=pipeline_result.plan.plan_id,
            event_type="compliance.completed",
            actor_type=AuditActorType.system,
            actor_id="3j-compliance",
            severity=(
                AuditSeverity.info
                if compliance.status.value == "passed"
                else AuditSeverity.warning
                if compliance.status.value == "warning"
                else AuditSeverity.error
            ),
            metadata={
                "status": compliance.status.value,
                "risk_score": compliance.risk_score,
            },
        )
        self.audit_store.emit(
            request_id=request.request_id,
            tenant_id=request.tenant_id,
            user_id=request.user_id,
            trace_id=context.trace_id,
            plan_id=pipeline_result.plan.plan_id,
            event_type="request.completed",
            actor_type=AuditActorType.system,
            actor_id="multi-agent-runtime",
            metadata={"grounded": pipeline_result.answer.grounded},
        )
        return GovernedRunResult(
            pipeline=pipeline_result,
            compliance=compliance,
            version_manifest=version_manifest,
        )
