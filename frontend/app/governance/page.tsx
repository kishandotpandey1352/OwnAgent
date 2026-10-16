"use client";

import { FormEvent, useEffect, useState } from "react";

type Metrics = {
  request_count: number;
  grounded_response_rate: number;
  compliance_pass_rate: number;
  agent_success_rate: number;
  agent_timeout_rate: number;
  average_agent_count: number;
  average_latency_ms: number;
  p95_latency_ms: number;
  average_cost_usd: number;
  p95_cost_usd: number;
  citation_validity_rate: number;
  queue_depth: number;
  provider_failure_rate: number;
};

type Alert = { alert_id: string; code: string; severity: string; message: string; state: string };

const pct = (value: number) => `${(value * 100).toFixed(1)}%`;

export default function GovernancePage() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [requestId, setRequestId] = useState("");
  const [audit, setAudit] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const [m, a] = await Promise.all([
      fetch("/api/phase3/governance/metrics", { cache: "no-store" }),
      fetch("/api/phase3/governance/alerts", { cache: "no-store" }),
    ]);
    if (!m.ok || !a.ok) throw new Error("Governance API is unavailable.");
    setMetrics(await m.json());
    setAlerts(await a.json());
  }

  useEffect(() => {
    refresh().catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  async function inspect(event: FormEvent) {
    event.preventDefault();
    if (!requestId.trim()) return;
    setError(null);
    const response = await fetch(`/api/phase3/governance/audit/${encodeURIComponent(requestId.trim())}`, { cache: "no-store" });
    const body = await response.json();
    if (!response.ok) {
      setError(body.detail || "Audit lookup failed.");
      return;
    }
    setAudit(body);
  }

  const cards = metrics ? [
    ["Requests", metrics.request_count.toString()],
    ["Grounded", pct(metrics.grounded_response_rate)],
    ["Compliance pass", pct(metrics.compliance_pass_rate)],
    ["Agent success", pct(metrics.agent_success_rate)],
    ["Citation validity", pct(metrics.citation_validity_rate)],
    ["p95 latency", `${Math.round(metrics.p95_latency_ms)} ms`],
    ["p95 cost", `$${metrics.p95_cost_usd.toFixed(4)}`],
    ["Queue depth", metrics.queue_depth.toString()],
  ] : [];

  return (
    <main style={{ maxWidth: 1180, margin: "0 auto", padding: "36px 24px", fontFamily: "system-ui" }}>
      <p style={{ letterSpacing: 2, fontSize: 12, fontWeight: 700, opacity: 0.65 }}>PHASE 3J</p>
      <h1 style={{ fontSize: 38, margin: "6px 0" }}>Governance & Audit Control Room</h1>
      <p style={{ maxWidth: 760, opacity: 0.75 }}>Deterministic compliance, grounded-response quality, agent health, cost and append-only request audit.</p>
      {error && <div style={{ margin: "20px 0", padding: 14, border: "1px solid #b91c1c", borderRadius: 10 }}>{error}</div>}

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 12, marginTop: 28 }}>
        {cards.map(([label, value]) => (
          <article key={label} style={{ border: "1px solid #d4d4d8", borderRadius: 14, padding: 18 }}>
            <div style={{ fontSize: 12, textTransform: "uppercase", opacity: 0.6 }}>{label}</div>
            <div style={{ fontSize: 28, fontWeight: 700, marginTop: 8 }}>{value}</div>
          </article>
        ))}
      </section>

      <section style={{ marginTop: 34 }}>
        <h2>Operational alerts</h2>
        {alerts.length === 0 ? <p style={{ opacity: 0.7 }}>No active threshold alerts.</p> : alerts.map((alert) => (
          <div key={alert.alert_id} style={{ border: "1px solid #d4d4d8", borderRadius: 10, padding: 14, marginBottom: 8 }}>
            <strong>{alert.severity.toUpperCase()} · {alert.code}</strong><div>{alert.message}</div>
          </div>
        ))}
      </section>

      <section style={{ marginTop: 34 }}>
        <h2>Request explorer</h2>
        <form onSubmit={inspect} style={{ display: "flex", gap: 8, maxWidth: 720 }}>
          <input value={requestId} onChange={(e) => setRequestId(e.target.value)} placeholder="request_id" style={{ flex: 1, padding: 12, border: "1px solid #a1a1aa", borderRadius: 8 }} />
          <button style={{ padding: "10px 18px", borderRadius: 8, border: "1px solid #18181b", cursor: "pointer" }}>Inspect</button>
        </form>
{audit != null && (
  <pre
    style={{
      marginTop: 16,
      padding: 18,
      borderRadius: 12,
      overflow: "auto",
      background: "rgba(127,127,127,.09)",
      fontSize: 12,
    }}
  >
    {JSON.stringify(audit, null, 2)}
  </pre>
)}      </section>
    </main>
  );
}
