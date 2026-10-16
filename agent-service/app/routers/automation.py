from __future__ import annotations

import json
import os
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import AgentRequest, ExecutionContext
from app.agents.governed_pipeline import GovernedMultiAgentPipeline
from app.automation import (
    ApprovalService,
    AutomationEngine,
    AutomationEvent,
    InMemoryDurableQueue,
    WebhookReplayStore,
    verify_webhook,
)
from app.core.config import settings
from app.routers.multi_agent_runtime import _limits, governance_service


router = APIRouter(prefix="/automation", tags=["automation"])
queue = InMemoryDurableQueue()
approvals = ApprovalService()
webhook_replays = WebhookReplayStore()


class ApprovalRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workflow_id: str
    tenant_id: str
    action: str
    original_payload: dict = Field(default_factory=dict)


class ApprovalDecisionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: bool

engine = AutomationEngine(
    runner=lambda event: {"event_id": event.event_id},
    audit=lambda event_type, metadata: governance_service.audit.emit(
        request_id=str(metadata.get("workflow_id") or metadata.get("event_id") or "automation"),
        tenant_id=metadata.get("tenant_id"),
        user_id=metadata.get("user_id"),
        event_type=event_type,
        actor_type="workflow",  # pydantic coerces enum values
        actor_id="automation-engine",
        metadata=metadata,
    ),
)


def _automation_enabled() -> bool:
    return bool(getattr(settings, "automation_enabled", False))


def _require_admin(role: str | None) -> None:
    if role not in {"administrator", "automation_admin"}:
        raise HTTPException(status_code=403, detail="Automation administrator role required.")


@router.post("/events")
def enqueue_event(
    event: AutomationEvent,
    x_tenant_id: str | None = Header(default=None),
    x_automation_role: str | None = Header(default=None),
):
    if x_automation_role not in {"producer", "administrator"}:
        raise HTTPException(status_code=403, detail="Automation producer role required.")
    if not x_tenant_id or x_tenant_id != event.tenant_id:
        raise HTTPException(status_code=403, detail="Automation event tenant scope mismatch.")
    if not _automation_enabled():
        raise HTTPException(status_code=503, detail="Automation is disabled by feature flag.")
    message = queue.enqueue(event)
    governance_service.queue_depth = queue.depth
    return {"accepted": True, "message_id": message.message_id, "queue_depth": queue.depth}


async def _run_governed_event(event: AutomationEvent):
    payload = event.payload
    question = str(payload.get("question") or "Analyze the uploaded financial document and summarize the relevant evidence.")
    document_ids = [str(item) for item in payload.get("document_ids", [])]
    if not document_ids and payload.get("document_id"):
        document_ids = [str(payload["document_id"])]
    dataset_id = payload.get("dataset_id")
    request_id = f"auto-{event.event_id}"
    trace_id = f"trace-{uuid4()}"
    user_id = event.user_id or "automation-service"
    request = AgentRequest(
        request_id=request_id,
        question=question,
        user_id=user_id,
        tenant_id=event.tenant_id,
        use_documents=bool(document_ids),
        document_ids=document_ids,
        dataset_id=str(dataset_id) if dataset_id else None,
        allow_web_fallback=bool(payload.get("allow_web_fallback", False)),
        trusted_web_domains=[str(item) for item in payload.get("trusted_web_domains", [])],
        metadata={"automation_event_id": event.event_id},
    )
    context = ExecutionContext(
        request_id=request_id,
        user_id=user_id,
        tenant_id=event.tenant_id,
        trace_id=trace_id,
        use_documents=bool(document_ids),
        document_ids=document_ids,
        dataset_id=str(dataset_id) if dataset_id else None,
        allow_web_fallback=request.allow_web_fallback,
        trusted_web_domains=request.trusted_web_domains,
        limits=_limits(),
        metadata={"automation_event_id": event.event_id},
    )
    governed = GovernedMultiAgentPipeline(audit_store=governance_service.audit)
    result = await governed.run(request=request, context=context)
    governance_service.record(
        execution=result.pipeline.execution,
        answer=result.pipeline.answer,
        compliance=result.compliance,
        tenant_id=event.tenant_id,
    )
    return result.model_dump(mode="json")


@router.post("/run-next")
async def run_next(x_audit_role: str | None = Header(default=None)):
    _require_admin(x_audit_role)
    message = queue.receive()
    governance_service.queue_depth = queue.depth
    if message is None:
        return {"processed": False, "reason": "queue_empty"}
    try:
        result = await engine.process_async(message.event, runner=_run_governed_event)
        return {"processed": True, "workflow": result.workflow, "duplicate": result.duplicate}
    except Exception as exc:
        outcome = queue.retry_or_dead_letter(
            message,
            error=type(exc).__name__,
            max_attempts=3,
            workflow_id=next((wf.workflow_id for wf in engine.workflows.values() if wf.event_id == message.event.event_id), None),
        )
        governance_service.queue_depth = queue.depth
        return {"processed": False, "retry_or_dlq": outcome}


@router.get("/status")
def status(x_audit_role: str | None = Header(default=None)):
    _require_admin(x_audit_role)
    return {
        "enabled": _automation_enabled(),
        "queue_depth": queue.depth,
        "workflows": list(engine.workflows.values()),
        "dlq_count": len(queue.dlq.list()),
    }


@router.get("/dlq")
def dlq(x_audit_role: str | None = Header(default=None)):
    _require_admin(x_audit_role)
    return queue.dlq.list()


@router.post("/dlq/{dlq_id}/replay")
def replay_dlq(dlq_id: str, x_audit_role: str | None = Header(default=None)):
    _require_admin(x_audit_role)
    try:
        event = queue.dlq.replay(dlq_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    message = queue.enqueue(event)
    governance_service.queue_depth = queue.depth
    return {"replayed": True, "message_id": message.message_id}


@router.post("/webhooks/{source}")
async def webhook(source: str, request: Request, x_webhook_signature: str | None = Header(default=None), x_webhook_timestamp: int | None = Header(default=None), x_delivery_id: str | None = Header(default=None)):
    if not _automation_enabled():
        raise HTTPException(status_code=503, detail="Automation is disabled by feature flag.")
    secret = os.getenv("AUTOMATION_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook secret is not configured.")
    if not x_webhook_signature or x_webhook_timestamp is None or not x_delivery_id:
        raise HTTPException(status_code=401, detail="Webhook authentication headers are missing.")
    body = await request.body()
    try:
        event = AutomationEvent.model_validate(json.loads(body))
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Webhook payload schema is invalid.") from exc
    if event.source != source:
        raise HTTPException(status_code=422, detail="Webhook source does not match route source.")
    try:
        verify_webhook(
            secret=secret,
            timestamp=x_webhook_timestamp,
            body=body,
            signature=x_webhook_signature,
            replay_store=webhook_replays,
            replay_key=f"{source}:{x_delivery_id}",
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Webhook verification failed.") from exc
    message = queue.enqueue(event)
    governance_service.queue_depth = queue.depth
    return {"accepted": True, "message_id": message.message_id}


@router.get("/approvals")
def list_approvals(
    x_tenant_id: str | None = Header(default=None),
    x_audit_role: str | None = Header(default=None),
):
    _require_admin(x_audit_role)
    return approvals.list(tenant_id=x_tenant_id, pending_only=False)


@router.post("/approvals")
def request_approval(
    payload: ApprovalRequestBody,
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
):
    if not x_tenant_id or x_tenant_id != payload.tenant_id:
        raise HTTPException(status_code=403, detail="Approval tenant scope mismatch.")
    requester = x_user_id or "local-demo-user"
    return approvals.request(
        workflow_id=payload.workflow_id,
        tenant_id=payload.tenant_id,
        requested_by=requester,
        action=payload.action,
        original_payload=payload.original_payload,
    )


@router.post("/approvals/{approval_id}/decision")
def decide_approval(
    approval_id: str,
    payload: ApprovalDecisionBody,
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_roles: str | None = Header(default=""),
):
    roles = {item.strip() for item in (x_roles or "").split(",") if item.strip()}
    if not x_tenant_id:
        raise HTTPException(status_code=403, detail="Approval decisions require tenant identity.")
    try:
        return approvals.decide(
            approval_id,
            actor_id=x_user_id or "local-demo-user",
            actor_roles=roles,
            approve=payload.approve,
            actor_tenant_id=x_tenant_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

@router.delete("/dlq/{dlq_id}")
def discard_dlq(dlq_id: str, x_audit_role: str | None = Header(default=None)):
    _require_admin(x_audit_role)
    try:
        queue.dlq.discard(dlq_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"discarded": True, "dlq_id": dlq_id}
