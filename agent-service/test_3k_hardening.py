from datetime import datetime, timezone

from app.automation import AutomationEngine, AutomationEvent, AutomationEventType

# Load/idempotency smoke: one hundred deliveries of the same event execute once.
now = datetime.now(timezone.utc)
event = AutomationEvent(
    event_type=AutomationEventType.analysis_completed,
    tenant_id="tenant-load",
    source="load-test",
    occurred_at=now,
    correlation_id="corr-load",
    idempotency_key="load:once",
    payload={"question": "test"},
)
calls = 0

def runner(evt):
    global calls
    calls += 1
    return {"event_id": evt.event_id}

engine = AutomationEngine(runner=runner)
results = [engine.process(event) for _ in range(100)]
assert calls == 1
assert sum(result.duplicate for result in results) == 99

# Tenant/event contract rejects missing tenant or naive timestamps through Pydantic.
try:
    AutomationEvent(
        event_type=AutomationEventType.analysis_completed,
        tenant_id="",
        source="bad",
        occurred_at=datetime.now(),
        correlation_id="c",
        idempotency_key="k",
    )
except Exception:
    pass
else:
    raise AssertionError("Invalid automation event must be rejected")

print("PASS: 3K-I duplicate-load and event-contract hardening smoke validated.")
