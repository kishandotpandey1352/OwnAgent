from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ApprovalDecision(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ApprovalRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "ApprovalRecord.v1"
    approval_id: str = Field(default_factory=lambda: f"approval-{uuid4()}")
    workflow_id: str
    tenant_id: str
    requested_by: str
    action: str
    original_payload: dict[str, Any]
    decision: ApprovalDecision = ApprovalDecision.pending
    decided_by: str | None = None
    requested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: datetime | None = None


class ApprovalService:
    def __init__(self) -> None:
        self._records: dict[str, ApprovalRecord] = {}

    def request(
        self,
        *,
        workflow_id: str,
        tenant_id: str,
        requested_by: str,
        action: str,
        original_payload: dict[str, Any],
    ) -> ApprovalRecord:
        record = ApprovalRecord(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            requested_by=requested_by,
            action=action,
            original_payload=original_payload,
        )
        self._records[record.approval_id] = record
        return record

    def decide(
        self,
        approval_id: str,
        *,
        actor_id: str,
        actor_roles: set[str],
        approve: bool,
        actor_tenant_id: str | None = None,
        enforce_maker_checker: bool = True,
    ) -> ApprovalRecord:
        record = self.get(approval_id)
        if actor_tenant_id is not None and actor_tenant_id != record.tenant_id:
            raise PermissionError("Approval is outside the actor's tenant scope.")
        if "approver" not in actor_roles and "administrator" not in actor_roles:
            raise PermissionError("Actor lacks approval permission.")
        if enforce_maker_checker and actor_id == record.requested_by:
            raise PermissionError("Requester cannot approve their own high-impact action.")
        if record.decision != ApprovalDecision.pending:
            raise ValueError("Approval has already been decided.")
        updated = record.model_copy(
            update={
                "decision": ApprovalDecision.approved if approve else ApprovalDecision.rejected,
                "decided_by": actor_id,
                "decided_at": datetime.now(timezone.utc),
            }
        )
        self._records[approval_id] = updated
        return updated

    def list(
        self,
        *,
        tenant_id: str | None = None,
        pending_only: bool = False,
    ) -> list[ApprovalRecord]:
        records = list(self._records.values())
        if tenant_id is not None:
            records = [item for item in records if item.tenant_id == tenant_id]
        if pending_only:
            records = [item for item in records if item.decision == ApprovalDecision.pending]
        return records

    def get(self, approval_id: str) -> ApprovalRecord:
        try:
            return self._records[approval_id]
        except KeyError as exc:
            raise KeyError(f"Unknown approval: {approval_id}") from exc
