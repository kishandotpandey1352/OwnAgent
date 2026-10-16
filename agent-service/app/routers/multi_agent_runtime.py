from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException

from app.agents.contracts import AgentRequest, ExecutionContext, ExecutionLimits
from app.agents.governed_pipeline import GovernedMultiAgentPipeline
from app.core.config import settings
from app.governance.service import GovernanceService
from app.schemas.multi_agent_runtime import MultiAgentAnalyzeRequest, MultiAgentAnalyzeResponse


router = APIRouter(prefix="/multi-agent", tags=["multi-agent"])
governance_service = GovernanceService()


def _limits() -> ExecutionLimits:
    return ExecutionLimits(
        max_agent_count=int(settings.multi_agent_max_agents_per_request),
        max_coordinator_rounds=int(settings.multi_agent_max_coordinator_rounds),
        max_retries_per_agent=int(settings.multi_agent_max_retries_per_agent),
        max_graph_depth=int(settings.multi_agent_max_graph_depth),
        max_web_searches=int(settings.multi_agent_max_web_searches),
        max_web_fetches=int(settings.multi_agent_max_web_fetches),
        request_timeout_seconds=float(settings.multi_agent_request_timeout_seconds),
        max_concurrency=int(settings.multi_agent_max_concurrency),
        max_llm_tokens=int(settings.multi_agent_max_llm_tokens),
        max_estimated_cost_usd=float(settings.multi_agent_max_estimated_cost_usd),
    )


@router.post("/analyze", response_model=MultiAgentAnalyzeResponse)
async def analyze_multi_agent(
    payload: MultiAgentAnalyzeRequest,
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
):
    if not bool(settings.multi_agent_enabled):
        raise HTTPException(status_code=503, detail="Multi-agent runtime is disabled by feature flag.")

    # These headers must be populated by trusted authentication middleware or
    # an API gateway that strips caller-supplied identity headers first. The
    # request payload is never accepted as identity authority.
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Authenticated user identity is required.")
    if payload.user_id and payload.user_id != x_user_id:
        raise HTTPException(status_code=403, detail="user_id does not match authenticated header scope.")
    if payload.tenant_id and not x_tenant_id:
        raise HTTPException(status_code=403, detail="Authenticated tenant identity is required for tenant-scoped requests.")
    if payload.tenant_id and payload.tenant_id != x_tenant_id:
        raise HTTPException(status_code=403, detail="tenant_id does not match authenticated header scope.")

    request_id = str(uuid4())
    trace_id = f"trace-{uuid4()}"
    user_id = x_user_id
    tenant_id = x_tenant_id

    request = AgentRequest(
        request_id=request_id,
        question=payload.question.strip(),
        user_id=user_id,
        tenant_id=tenant_id,
        provider_id=payload.provider_id,
        use_documents=payload.use_documents,
        document_ids=payload.document_ids,
        top_k=payload.top_k,
        dataset_id=payload.dataset_id,
        allow_web_fallback=payload.allow_web_fallback,
        trusted_web_domains=payload.trusted_web_domains,
        metadata=payload.metadata,
    )
    context = ExecutionContext(
        request_id=request_id,
        user_id=user_id,
        tenant_id=tenant_id,
        trace_id=trace_id,
        provider_id=payload.provider_id,
        use_documents=payload.use_documents,
        document_ids=payload.document_ids,
        top_k=payload.top_k,
        dataset_id=payload.dataset_id,
        allow_web_fallback=payload.allow_web_fallback,
        trusted_web_domains=payload.trusted_web_domains,
        limits=_limits(),
        metadata=payload.metadata,
    )

    pipeline = GovernedMultiAgentPipeline(audit_store=governance_service.audit)
    try:
        result = await pipeline.run(request=request, context=context)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Multi-agent execution failed safely.") from exc

    governance_service.record(
        execution=result.pipeline.execution,
        answer=result.pipeline.answer,
        compliance=result.compliance,
        tenant_id=tenant_id,
    )
    if bool(getattr(settings, "compliance_blocking_enabled", False)) and result.compliance.status.value == "failed":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "COMPLIANCE_BLOCKED",
                "request_id": request_id,
                "risk_score": result.compliance.risk_score,
            },
        )
    return MultiAgentAnalyzeResponse(
        request_id=request_id,
        trace_id=trace_id,
        answer=result.pipeline.answer,
        plan=result.pipeline.plan,
        execution=result.pipeline.execution,
        review=result.pipeline.review,
        compliance=result.compliance,
        pre_execution_budget=result.pipeline.pre_execution_budget,
        post_execution_budget=result.pipeline.post_execution_budget,
        trace=result.pipeline.trace,
        version_manifest=result.version_manifest,
    )
