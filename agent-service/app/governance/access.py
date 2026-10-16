from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict

from app.governance.audit import AuditEvent


class AuditRole(str, Enum):
    user = "user"
    analyst = "analyst"
    auditor = "auditor"
    administrator = "administrator"


class AuditPrincipal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    tenant_id: str | None = None
    role: AuditRole = AuditRole.user


def can_view_audit_event(principal: AuditPrincipal, event: AuditEvent) -> bool:
    """Tenant isolation first, then role-based access."""

    if event.tenant_id != principal.tenant_id:
        return False
    if principal.role in {AuditRole.auditor, AuditRole.administrator}:
        return True
    if principal.role == AuditRole.analyst:
        return event.severity.value != "critical"
    return event.user_id == principal.user_id


def filter_visible_events(
    principal: AuditPrincipal,
    events: list[AuditEvent],
) -> list[AuditEvent]:
    return [event for event in events if can_view_audit_event(principal, event)]
