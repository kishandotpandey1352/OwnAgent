from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.governance.access import AuditPrincipal, AuditRole, filter_visible_events
from app.governance.alerts import evaluate_alerts
from app.routers.multi_agent_runtime import governance_service


router = APIRouter(prefix="/governance", tags=["governance"])


def _principal(
    *,
    user_id: str | None,
    tenant_id: str | None,
    role: str | None,
) -> AuditPrincipal:
    if not user_id:
        raise HTTPException(status_code=401, detail="Authenticated user identity is required.")
    try:
        parsed_role = AuditRole(role or "user")
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Unknown audit role.") from exc
    return AuditPrincipal(
        user_id=user_id,
        tenant_id=tenant_id,
        role=parsed_role,
    )


def _require_governance_role(role: str | None) -> None:
    if role not in {"analyst", "auditor", "administrator"}:
        raise HTTPException(status_code=403, detail="Governance role required.")


@router.get("/metrics")
def metrics(
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_audit_role: str | None = Header(default=None),
):
    _require_governance_role(x_audit_role)
    principal = _principal(user_id=x_user_id, tenant_id=x_tenant_id, role=x_audit_role)
    if principal.role != AuditRole.administrator and not principal.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant identity is required for scoped metrics.")
    tenant_scope = None if principal.role == AuditRole.administrator else principal.tenant_id
    return governance_service.metrics(tenant_id=tenant_scope)


@router.get("/alerts")
def alerts(
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_audit_role: str | None = Header(default=None),
):
    _require_governance_role(x_audit_role)
    principal = _principal(user_id=x_user_id, tenant_id=x_tenant_id, role=x_audit_role)
    if principal.role != AuditRole.administrator and not principal.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant identity is required for scoped alerts.")
    tenant_scope = None if principal.role == AuditRole.administrator else principal.tenant_id
    metrics_snapshot = governance_service.metrics(tenant_id=tenant_scope)
    return evaluate_alerts(
        metrics_snapshot,
        compliance_reports=governance_service.compliance_for_tenant(tenant_scope),
    )


@router.get("/audit/{request_id}")
def audit_request(
    request_id: str,
    x_user_id: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None),
    x_audit_role: str | None = Header(default="user"),
):
    principal = _principal(
        user_id=x_user_id,
        tenant_id=x_tenant_id,
        role=x_audit_role,
    )
    events = governance_service.audit.list_events(request_id=request_id)
    visible = filter_visible_events(principal, events)
    if events and not visible:
        raise HTTPException(status_code=403, detail="Audit request is outside the caller's scope.")
    return {"request_id": request_id, "events": visible}
