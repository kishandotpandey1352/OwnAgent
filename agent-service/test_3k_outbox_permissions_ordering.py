from datetime import datetime, timezone

from app.automation import (
    AutomationEvent,
    AutomationEventType,
    AutomationPermission,
    InMemoryOutbox,
    ordering_policy,
    scoped_filing_analysis_identity,
)

now = datetime.now(timezone.utc)
event = AutomationEvent(
    event_type=AutomationEventType.document_uploaded,
    tenant_id="t1",
    source="upload",
    occurred_at=now,
    correlation_id="c1",
    idempotency_key="doc1:v1",
    payload={"document_id": "doc-1"},
)

outbox = InMemoryOutbox()
record = outbox.add(event)
published = []
assert outbox.publish_pending(lambda evt: published.append(evt.event_id)) == 1
assert published == [event.event_id]
assert outbox.pending() == []

ordering = ordering_policy(event)
assert ordering.requires_ordering is True
assert ordering.ordering_key == "t1:document:doc-1"

identity = scoped_filing_analysis_identity("t1")
identity.authorize(AutomationPermission.run_finance_agents, tenant_id="t1")
try:
    identity.authorize(AutomationPermission.send_external_message, tenant_id="t1")
except PermissionError:
    pass
else:
    raise AssertionError("Workflow permissions must deny ungranted external action")
try:
    identity.authorize(AutomationPermission.run_finance_agents, tenant_id="t2")
except PermissionError:
    pass
else:
    raise AssertionError("Workflow identity must enforce tenant isolation")

print("PASS: 3K transactional-outbox contract, ordering policy and workflow least privilege validated.")
