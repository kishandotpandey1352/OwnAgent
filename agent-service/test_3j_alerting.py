from app.governance.alerts import AlertThresholds, evaluate_alerts
from app.governance.metrics import MetricsSnapshot

metrics = MetricsSnapshot(
    request_count=100,
    grounded_response_rate=0.95,
    compliance_pass_rate=0.90,
    agent_success_rate=0.80,
    agent_timeout_rate=0.10,
    average_agent_count=3,
    average_latency_ms=5000,
    p95_latency_ms=45000,
    average_cost_usd=0.10,
    p95_cost_usd=0.40,
    citation_validity_rate=0.95,
    queue_depth=5000,
    provider_failure_rate=0.10,
)
alerts = evaluate_alerts(metrics, thresholds=AlertThresholds())
codes = {alert.code for alert in alerts}
assert {
    "P95_LATENCY_HIGH",
    "AGENT_FAILURE_RATE_HIGH",
    "CITATION_VALIDITY_LOW",
    "P95_COST_HIGH",
    "QUEUE_BACKLOG_HIGH",
    "PROVIDER_FAILURE_HIGH",
}.issubset(codes)
assert all(alert.owner and alert.runbook for alert in alerts)
print("PASS: 3J-F alert thresholds produce owned/runbook-backed operational alerts.")
