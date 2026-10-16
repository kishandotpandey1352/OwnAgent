"use client";

import { useEffect, useMemo, useState } from "react";

type UserMemoryType =
  | "answer_style"
  | "chart_preference"
  | "domain_focus"
  | "risk_tone"
  | "provider_preference";

type UserMemoryRecord = {
  id: string;
  user_id: string;
  memory_type: UserMemoryType;
  memory_key: string;
  memory_value: string;
  confidence: number;
  source: string;
  status: "proposed" | "active" | "deleted";
  is_active: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  confirmed_at?: string | null;
  deleted_at?: string | null;
};

type MemoryListResponse = {
  ok: boolean;
  memories?: UserMemoryRecord[];
  error?: string;
  detail?: string;
};

const memoryTypeOptions: {
  value: UserMemoryType;
  label: string;
  description: string;
  defaultKey: string;
  defaultValue: string;
}[] = [
  {
    value: "answer_style",
    label: "Answer style",
    description: "How responses should be written.",
    defaultKey: "preferred_response_style",
    defaultValue:
      "Prefer concise finance answers with clear bullets and tables when useful.",
  },
  {
    value: "chart_preference",
    label: "Chart preference",
    description: "Preferred chart types for trends, comparisons, and ratios.",
    defaultKey: "preferred_chart_style",
    defaultValue:
      "Prefer line charts for trends and bar charts for company comparisons.",
  },
  {
    value: "domain_focus",
    label: "Domain focus",
    description: "General finance topics you often analyze.",
    defaultKey: "common_analysis_focus",
    defaultValue:
      "Often focuses on annual reports, revenue growth, margins, liquidity, and risk factors.",
  },
  {
    value: "risk_tone",
    label: "Risk tone",
    description: "How conservative or direct risk explanations should be.",
    defaultKey: "preferred_risk_tone",
    defaultValue:
      "Prefer conservative risk language and avoid overstating financial conclusions.",
  },
  {
    value: "provider_preference",
    label: "Provider preference",
    description: "Cost, speed, or quality preference for model routing.",
    defaultKey: "preferred_provider_routing",
    defaultValue:
      "Prefer cheaper premium providers unless higher quality is needed.",
  },
];

function getMemoryTypeLabel(type: UserMemoryType) {
  return memoryTypeOptions.find((option) => option.value === type)?.label ?? type;
}

function formatDate(value?: string | null) {
  if (!value) return "Not confirmed";

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function Pill({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: "emerald" | "cyan" | "amber" | "rose" | "slate";
}) {
  const toneClass =
    tone === "emerald"
      ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"
      : tone === "cyan"
        ? "border-cyan-300/20 bg-cyan-300/10 text-cyan-100"
        : tone === "amber"
          ? "border-amber-300/20 bg-amber-300/10 text-amber-100"
          : tone === "rose"
            ? "border-rose-300/20 bg-rose-300/10 text-rose-100"
            : "border-white/10 bg-white/5 text-slate-300";

  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold ${toneClass}`}
    >
      {children}
    </span>
  );
}

export function MemoryPreferencesDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [memories, setMemories] = useState<UserMemoryRecord[]>([]);
  const [memoryType, setMemoryType] =
    useState<UserMemoryType>("answer_style");
  const [memoryKey, setMemoryKey] = useState("preferred_response_style");
  const [memoryValue, setMemoryValue] = useState(
    "Prefer concise finance answers with clear bullets and tables when useful.",
  );

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const activeMemories = useMemo(
    () =>
      memories.filter(
        (memory) => memory.status === "active" && memory.is_active,
      ),
    [memories],
  );

  const proposedMemories = useMemo(
    () => memories.filter((memory) => memory.status === "proposed"),
    [memories],
  );

  useEffect(() => {
    if (open) {
      void loadMemories();
    }
  }, [open]);

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onClose();
      }
    }

    if (open) {
      document.addEventListener("keydown", handleEscape);
    }

    return () => {
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open, onClose]);

  function handleMemoryTypeChange(nextType: UserMemoryType) {
    const option = memoryTypeOptions.find((item) => item.value === nextType);

    setMemoryType(nextType);

    if (option) {
      setMemoryKey(option.defaultKey);
      setMemoryValue(option.defaultValue);
    }
  }

  async function loadMemories() {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/agent-memory/list", {
        cache: "no-store",
      });

      const payload = (await response.json()) as MemoryListResponse;

      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.error ?? payload.detail ?? "Failed to load memory.",
        );
      }

      setMemories(payload.memories ?? []);
    } catch (loadError) {
      setError(
        loadError instanceof Error
          ? loadError.message
          : "Failed to load memory.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function proposeMemory() {
    setSaving(true);
    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/agent-memory/propose", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          memory_type: memoryType,
          memory_key: memoryKey,
          memory_value: memoryValue,
          confidence: 0.8,
          source: "user-entered",
          metadata: {
            created_from: "settings_memory_dialog",
          },
        }),
      });

      const payload = (await response.json()) as MemoryListResponse;

      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.error ?? payload.detail ?? "Failed to propose memory.",
        );
      }

      setStatusMessage("Memory proposed. Confirm it before agents can use it.");
      await loadMemories();
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Failed to propose memory.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function confirmMemory(memoryId: string) {
    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/agent-memory/confirm", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          memory_id: memoryId,
        }),
      });

      const payload = (await response.json()) as MemoryListResponse;

      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.error ?? payload.detail ?? "Failed to confirm memory.",
        );
      }

      setStatusMessage("Memory confirmed and active.");
      await loadMemories();
    } catch (confirmError) {
      setError(
        confirmError instanceof Error
          ? confirmError.message
          : "Failed to confirm memory.",
      );
    }
  }

  async function deleteMemory(memoryId: string) {
    const confirmed = window.confirm("Delete this saved memory?");

    if (!confirmed) return;

    setError(null);
    setStatusMessage(null);

    try {
      const response = await fetch("/api/agent-memory/delete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          memory_id: memoryId,
        }),
      });

      const payload = (await response.json()) as MemoryListResponse;

      if (!response.ok || !payload.ok) {
        throw new Error(
          payload.error ?? payload.detail ?? "Failed to delete memory.",
        );
      }

      setStatusMessage("Memory deleted.");
      await loadMemories();
    } catch (deleteError) {
      setError(
        deleteError instanceof Error
          ? deleteError.message
          : "Failed to delete memory.",
      );
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto bg-black/70 px-3 py-6 backdrop-blur-sm">
      <div className="w-full max-w-5xl rounded-3xl border border-white/10 bg-slate-950 shadow-2xl shadow-black/50">
        <div className="sticky top-0 z-10 rounded-t-3xl border-b border-white/10 bg-slate-950/95 px-5 py-4 backdrop-blur">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/70">
                Memory Preferences
              </p>
              <h2 className="mt-2 text-xl font-semibold text-white">
                Manage confirmed agent preferences
              </h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-slate-400">
                Memory changes answer style, tone, and workflow only. It should
                not be treated as financial evidence.
              </p>

              <div className="mt-3 flex flex-wrap gap-2">
                <Pill tone="emerald">{activeMemories.length} active</Pill>
                <Pill tone="amber">{proposedMemories.length} proposed</Pill>
                <Pill>Explicit approval required</Pill>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void loadMemories()}
                disabled={loading}
                className="rounded-xl border border-cyan-300/20 bg-cyan-300/10 px-4 py-2 text-sm font-semibold text-cyan-50 transition hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Refreshing..." : "Refresh"}
              </button>

              <button
                type="button"
                onClick={onClose}
                className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-200 transition hover:bg-white/10"
              >
                Close
              </button>
            </div>
          </div>
        </div>

        <div className="grid gap-4 p-4 lg:grid-cols-[360px_minmax(0,1fr)]">
          <section className="rounded-3xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">
              Add preference
            </p>

            <h3 className="mt-2 text-lg font-semibold text-white">
              Propose memory
            </h3>

            <p className="mt-1 text-sm leading-6 text-slate-400">
              Proposed memories are not used until you confirm them.
            </p>

            <div className="mt-4 space-y-4">
              <label className="block space-y-2">
                <span className="text-sm font-semibold text-slate-200">
                  Memory type
                </span>
                <select
                  value={memoryType}
                  onChange={(event) =>
                    handleMemoryTypeChange(event.target.value as UserMemoryType)
                  }
                  className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none focus:border-cyan-300/40"
                >
                  {memoryTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <p className="text-xs leading-5 text-slate-500">
                  {
                    memoryTypeOptions.find(
                      (option) => option.value === memoryType,
                    )?.description
                  }
                </p>
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-semibold text-slate-200">
                  Memory key
                </span>
                <input
                  value={memoryKey}
                  onChange={(event) => setMemoryKey(event.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40"
                  placeholder="preferred_response_style"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-semibold text-slate-200">
                  Preference
                </span>
                <textarea
                  value={memoryValue}
                  onChange={(event) => setMemoryValue(event.target.value)}
                  rows={5}
                  className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm leading-6 text-white outline-none placeholder:text-slate-500 focus:border-cyan-300/40"
                  placeholder="Example: Prefer concise answers with tables and charts when helpful."
                />
              </label>

              <button
                type="button"
                onClick={() => void proposeMemory()}
                disabled={saving}
                className="w-full rounded-xl bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {saving ? "Saving..." : "Propose memory"}
              </button>
            </div>
          </section>

          <section className="space-y-4">
            {error ? (
              <p className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </p>
            ) : null}

            {statusMessage ? (
              <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
                {statusMessage}
              </p>
            ) : null}

            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-emerald-200/70">
                    Active
                  </p>
                  <h3 className="mt-2 text-lg font-semibold text-white">
                    Confirmed preferences
                  </h3>
                </div>

                <Pill tone="emerald">{activeMemories.length} active</Pill>
              </div>

              <div className="mt-4 space-y-3">
                {activeMemories.length ? (
                  activeMemories.map((memory) => (
                    <div
                      key={memory.id}
                      className="rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap gap-2">
                            <Pill tone="emerald">Active</Pill>
                            <Pill>{getMemoryTypeLabel(memory.memory_type)}</Pill>
                          </div>

                          <p className="mt-3 text-sm font-semibold text-white">
                            {memory.memory_value}
                          </p>

                          <p className="mt-2 text-xs text-slate-400">
                            Key: {memory.memory_key} · Confirmed:{" "}
                            {formatDate(memory.confirmed_at)}
                          </p>
                        </div>

                        <button
                          type="button"
                          onClick={() => void deleteMemory(memory.id)}
                          className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-rose-300/30 hover:bg-rose-300/10 hover:text-rose-100"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/15 bg-black/20 p-6 text-center">
                    <p className="text-sm font-medium text-slate-300">
                      No active memories yet.
                    </p>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      Propose and confirm a memory before agents can use it.
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-3xl border border-white/10 bg-black/20 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-amber-200/70">
                    Proposed
                  </p>
                  <h3 className="mt-2 text-lg font-semibold text-white">
                    Waiting for confirmation
                  </h3>
                </div>

                <Pill tone="amber">{proposedMemories.length} proposed</Pill>
              </div>

              <div className="mt-4 space-y-3">
                {proposedMemories.length ? (
                  proposedMemories.map((memory) => (
                    <div
                      key={memory.id}
                      className="rounded-2xl border border-amber-300/20 bg-amber-300/10 p-3"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div className="min-w-0">
                          <div className="flex flex-wrap gap-2">
                            <Pill tone="amber">Needs approval</Pill>
                            <Pill>{getMemoryTypeLabel(memory.memory_type)}</Pill>
                          </div>

                          <p className="mt-3 text-sm font-semibold text-white">
                            {memory.memory_value}
                          </p>

                          <p className="mt-2 text-xs text-slate-400">
                            Key: {memory.memory_key} · Proposed:{" "}
                            {formatDate(memory.created_at)}
                          </p>
                        </div>

                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={() => void confirmMemory(memory.id)}
                            className="rounded-xl border border-emerald-300/30 bg-emerald-300/10 px-3 py-2 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-300/20"
                          >
                            Confirm
                          </button>

                          <button
                            type="button"
                            onClick={() => void deleteMemory(memory.id)}
                            className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-rose-300/30 hover:bg-rose-300/10 hover:text-rose-100"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/15 bg-black/20 p-6 text-center">
                    <p className="text-sm font-medium text-slate-300">
                      No proposed memories.
                    </p>
                    <p className="mt-2 text-xs leading-5 text-slate-500">
                      Chat-style memory suggestions will appear here later.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}