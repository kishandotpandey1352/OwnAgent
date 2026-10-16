"use client";

import { useEffect, useState } from "react";

type Status = {
  enabled: boolean;
  queue_depth: number;
  workflows: Array<{ workflow_id: string; state: string; event_id: string }>;
  dlq_count: number;
};
type DlqItem = { dlq_id: string; error_category: string; attempt_count: number; event: { event_id: string; event_type: string } };
type Approval = { approval_id: string; workflow_id: string; tenant_id: string; action: string; decision: string; requested_by: string };

const card: React.CSSProperties = { border: "1px solid #d4d4d8", borderRadius: 14, padding: 18 };
const button: React.CSSProperties = { padding: "9px 14px", border: "1px solid #18181b", borderRadius: 8, cursor: "pointer", background: "transparent" };

export default function AutomationPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [dlq, setDlq] = useState<DlqItem[]>([]);
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    const [s, d, a] = await Promise.all([
      fetch("/api/phase3/automation/status", { cache: "no-store" }),
      fetch("/api/phase3/automation/dlq", { cache: "no-store" }),
      fetch("/api/phase3/automation/approvals", { cache: "no-store" }),
    ]);
    if (s.ok) setStatus(await s.json());
    if (d.ok) setDlq(await d.json());
    if (a.ok) setApprovals(await a.json());
  }

  useEffect(() => { void refresh(); }, []);

  async function runNext() {
    setMessage("Processing next queued workflow...");
    const response = await fetch("/api/phase3/automation/run-next", { method: "POST" });
    setMessage(JSON.stringify(await response.json()));
    await refresh();
  }

  async function decide(approvalId: string, tenantId: string, approve: boolean) {
    const response = await fetch(`/api/phase3/automation/approvals/${encodeURIComponent(approvalId)}/decision`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ approve, tenant_id: tenantId }),
    });
    setMessage(JSON.stringify(await response.json()));
    await refresh();
  }

  async function replay(dlqId: string) {
    const response = await fetch(`/api/phase3/automation/dlq/${encodeURIComponent(dlqId)}/replay`, { method: "POST" });
    setMessage(JSON.stringify(await response.json()));
    await refresh();
  }

  async function discard(dlqId: string) {
    const response = await fetch(`/api/phase3/automation/dlq/${encodeURIComponent(dlqId)}`, { method: "DELETE" });
    setMessage(JSON.stringify(await response.json()));
    await refresh();
  }

  return (
    <main style={{ maxWidth: 1180, margin: "0 auto", padding: "36px 24px", fontFamily: "system-ui" }}>
      <p style={{ letterSpacing: 2, fontSize: 12, fontWeight: 700, opacity: 0.65 }}>PHASE 3K</p>
      <h1 style={{ fontSize: 38, margin: "6px 0" }}>Event-Driven Automation</h1>
      <p style={{ maxWidth: 800, opacity: 0.75 }}>Queue health, explicit workflow state, maker-checker approvals, and dead-letter recovery for governed agent workflows.</p>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))", gap: 12, marginTop: 28 }}>
        <article style={card}><div>Feature flag</div><strong>{status?.enabled ? "ENABLED" : "DISABLED"}</strong></article>
        <article style={card}><div>Queue depth</div><strong style={{ fontSize: 28 }}>{status?.queue_depth ?? "—"}</strong></article>
        <article style={card}><div>DLQ</div><strong style={{ fontSize: 28 }}>{status?.dlq_count ?? "—"}</strong></article>
        <article style={card}><div>Waiting approvals</div><strong style={{ fontSize: 28 }}>{approvals.filter((item) => item.decision === "pending").length}</strong></article>
      </section>

      <div style={{ marginTop: 24 }}>
        <button onClick={runNext} style={button}>Run next queued item</button>
        {message && <p style={{ opacity: 0.75, wordBreak: "break-word" }}>{message}</p>}
      </div>

      <section style={{ marginTop: 34 }}>
        <h2>Workflow state</h2>
        <pre style={{ padding: 18, borderRadius: 12, overflow: "auto", background: "rgba(127,127,127,.09)", fontSize: 12 }}>{JSON.stringify(status?.workflows ?? [], null, 2)}</pre>
      </section>

      <section style={{ marginTop: 34 }}>
        <h2>Human approvals</h2>
        {approvals.length === 0 ? <p style={{ opacity: 0.7 }}>No approval records.</p> : approvals.map((item) => (
          <article key={item.approval_id} style={{ ...card, marginBottom: 10 }}>
            <strong>{item.action}</strong><div style={{ opacity: 0.7 }}>Workflow {item.workflow_id} · {item.decision}</div>
            {item.decision === "pending" && <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button style={button} onClick={() => decide(item.approval_id, item.tenant_id, true)}>Approve</button>
              <button style={button} onClick={() => decide(item.approval_id, item.tenant_id, false)}>Reject</button>
            </div>}
          </article>
        ))}
      </section>

      <section style={{ marginTop: 34 }}>
        <h2>Dead-letter queue</h2>
        {dlq.length === 0 ? <p style={{ opacity: 0.7 }}>DLQ is empty.</p> : dlq.map((item) => (
          <article key={item.dlq_id} style={{ ...card, marginBottom: 10 }}>
            <strong>{item.error_category}</strong><div style={{ opacity: 0.7 }}>Attempts {item.attempt_count} · {item.event?.event_type}</div>
            <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
              <button style={button} onClick={() => replay(item.dlq_id)}>Replay</button>
              <button style={button} onClick={() => discard(item.dlq_id)}>Discard</button>
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
