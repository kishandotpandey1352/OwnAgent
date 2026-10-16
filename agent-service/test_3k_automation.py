from datetime import datetime, timedelta, timezone

from app.automation import (
    ApprovalDecision,
    ApprovalService,
    AutomationEngine,
    AutomationEvent,
    AutomationEventType,
    DailySchedule,
    DeadLetterItem,
    InMemoryDurableQueue,
    ScheduleLeaseStore,
    WebhookReplayStore,
    WebhookVerificationError,
    WorkflowRecord,
    WorkflowState,
    WorkflowStateMachine,
    sign_webhook,
    verify_webhook,
)

now = datetime.now(timezone.utc)
event = AutomationEvent(
    event_type=AutomationEventType.document_uploaded,
    tenant_id="tenant-1",
    user_id="user-1",
    source="upload-api",
    occurred_at=now,
    correlation_id="corr-1",
    idempotency_key="tenant-1:document:abc:v1",
    payload={"document_id": "doc-1"},
)

calls = []
engine = AutomationEngine(runner=lambda evt: calls.append(evt.event_id) or {"ok": True})
first = engine.process(event)
second = engine.process(event)
assert first.workflow.state == WorkflowState.completed
assert second.duplicate is True
assert calls == [event.event_id]

machine = WorkflowStateMachine()
record = WorkflowRecord(workflow_id="wf-1", event_id=event.event_id, tenant_id="tenant-1")
running = machine.transition(record, WorkflowState.running)
assert running.state == WorkflowState.running
try:
    machine.transition(running, WorkflowState.pending)
except ValueError:
    pass
else:
    raise AssertionError("Invalid state transition should fail")

queue = InMemoryDurableQueue()
message = queue.enqueue(event)
received = queue.receive(now=datetime.now(timezone.utc) + timedelta(seconds=1))
assert received is not None and received.message_id == message.message_id
r1 = queue.retry_or_dead_letter(received, error="TEMP", max_attempts=2, base_delay_seconds=0)
assert not isinstance(r1, DeadLetterItem)
r2_msg = queue.receive(now=datetime.now(timezone.utc) + timedelta(seconds=1))
assert r2_msg is not None
r2 = queue.retry_or_dead_letter(r2_msg, error="TEMP", max_attempts=2, base_delay_seconds=0)
assert isinstance(r2, DeadLetterItem)
assert len(queue.dlq.list()) == 1
replayed = queue.dlq.replay(r2.dlq_id)
assert replayed.event_id == event.event_id

replay_store = WebhookReplayStore()
secret = "test-secret"
body = b'{"event":"document.uploaded"}'
timestamp = int(now.timestamp())
signature = sign_webhook(secret, timestamp=timestamp, body=body)
verify_webhook(
    secret=secret,
    timestamp=timestamp,
    body=body,
    signature=signature,
    replay_store=replay_store,
    replay_key="delivery-1",
    now=now,
)
try:
    verify_webhook(
        secret=secret,
        timestamp=timestamp,
        body=body,
        signature=signature,
        replay_store=replay_store,
        replay_key="delivery-1",
        now=now,
    )
except WebhookVerificationError:
    pass
else:
    raise AssertionError("Webhook replay must be rejected")

approvals = ApprovalService()
approval = approvals.request(
    workflow_id="wf-approval",
    tenant_id="tenant-1",
    requested_by="maker",
    action="modify-external-system",
    original_payload={"target": "example"},
)
try:
    approvals.decide(approval.approval_id, actor_id="maker", actor_roles={"approver"}, approve=True)
except PermissionError:
    pass
else:
    raise AssertionError("Maker-checker policy must block self approval")
approved = approvals.decide(
    approval.approval_id,
    actor_id="checker",
    actor_roles={"approver"},
    approve=True,
)
assert approved.decision == ApprovalDecision.approved

schedule = DailySchedule(schedule_id="daily-1", timezone="Europe/London", hour=8, minute=30)
next_run = schedule.next_run(now)
assert next_run > now.astimezone(next_run.tzinfo)
leases = ScheduleLeaseStore()
assert leases.acquire(schedule.schedule_id, next_run) is True
assert leases.acquire(schedule.schedule_id, next_run) is False

print("PASS: 3K contracts, idempotency, queue/DLQ, state machine, webhook security, scheduler and approvals validated.")

# Europe/London moves from GMT to BST on 2026-03-29. 01:30 local is a DST gap.
from zoneinfo import ZoneInfo
spring = datetime(2026, 3, 29, 0, 30, tzinfo=ZoneInfo("Europe/London"))
gap_schedule = DailySchedule(
    schedule_id="dst-gap",
    timezone="Europe/London",
    hour=1,
    minute=30,
    dst_gap_policy="shift_forward",
)
gap_next = gap_schedule.next_run(spring)
assert gap_next.hour == 2 and gap_next.minute == 30
assert gap_next.utcoffset() == timedelta(hours=1)

# A transiently failed idempotent event may be retried by the worker, but a completed event never re-runs.
import asyncio
retry_event = AutomationEvent(
    event_type=AutomationEventType.analysis_completed,
    tenant_id="tenant-retry",
    source="retry-test",
    occurred_at=now,
    correlation_id="corr-retry",
    idempotency_key="retry-once",
    payload={},
)
retry_engine = AutomationEngine(runner=lambda evt: None)
attempts = {"count": 0}
async def flaky(evt):
    attempts["count"] += 1
    if attempts["count"] == 1:
        raise RuntimeError("transient")
    return {"ok": True}
async def retry_case():
    try:
        await retry_engine.process_async(retry_event, runner=flaky)
    except RuntimeError:
        pass
    second = await retry_engine.process_async(retry_event, runner=flaky)
    third = await retry_engine.process_async(retry_event, runner=flaky)
    assert second.duplicate is False
    assert third.duplicate is True
    assert attempts["count"] == 2
asyncio.run(retry_case())
