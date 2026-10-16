from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.automation.contracts import AutomationEvent, AutomationEventType


class OrderingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requires_ordering: bool
    ordering_key: str | None = None
    reason: str


def ordering_policy(event: AutomationEvent) -> OrderingDecision:
    """Declare ordering requirements explicitly; never promise global ordering."""

    if event.event_type in {
        AutomationEventType.document_uploaded,
        AutomationEventType.document_indexed,
        AutomationEventType.analysis_completed,
    }:
        document_id = event.payload.get("document_id")
        if document_id:
            return OrderingDecision(
                requires_ordering=True,
                ordering_key=f"{event.tenant_id}:document:{document_id}",
                reason="Document lifecycle events must stay ordered per tenant/document.",
            )
    return OrderingDecision(
        requires_ordering=False,
        reason="This event has no declared ordering requirement.",
    )
