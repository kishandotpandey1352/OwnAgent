"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ChatPanel } from "@/components/ChatPanel";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { getProviderById, providerCatalog } from "@/lib/models";
import type {
  AppMode,
  AuthState,
  FinanceTask,
  HistoryEntry,
  ProviderOption,
} from "@/types";

import { AppTopMenu } from "@/components/AppTopMenu";


type BackendHealth = {
  status?: string;
  service?: string;
  model_id?: string;
};

type BackendReady = {
  ready?: boolean;
  model_loaded?: boolean;
  adapter_loaded?: boolean;
  model_id?: string;
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8008";
const defaultApiKey =
  process.env.NEXT_PUBLIC_DEFAULT_API_KEY ?? "dev-finance-api-key";

function StatusPill({
  label,
  tone,
}: {
  label: string;
  tone: "good" | "warn" | "bad" | "neutral";
}) {
  const toneClass =
    tone === "good"
      ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
      : tone === "warn"
        ? "border-amber-400/30 bg-amber-400/10 text-amber-200"
        : tone === "bad"
          ? "border-rose-400/30 bg-rose-400/10 text-rose-200"
          : "border-white/10 bg-white/5 text-slate-300";

  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold ${toneClass}`}
    >
      {label}
    </span>
  );
}

function InfoCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
      <p className="text-[11px] uppercase tracking-[0.2em] text-slate-500">
        {title}
      </p>
      <div className="mt-3 space-y-2">{children}</div>
    </div>
  );
}

function InfoRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-white/5 pb-2 last:border-b-0 last:pb-0">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="max-w-[60%] break-words text-right text-xs font-semibold text-white">
        {value}
      </span>
    </div>
  );
}

function getProviderRouteLabel(provider: ProviderOption) {
  if (provider.tier === "basic") {
    return "Basic";
  }

  return "Premium";
}

function modeLabel(mode: Exclude<AppMode, "compare">) {
  return mode === "basic" ? "Basic" : "Premium";
}

function taskLabel(task: FinanceTask) {
  if (task === "qa") return "Q&A";
  if (task === "risk-analysis") return "Risk Analysis";
  return "Summarize";
}

export default function DashboardPage() {
  const router = useRouter();

  const [auth, setAuth] = useState<AuthState | null>(null);
  const [mode, setMode] = useState<Exclude<AppMode, "compare">>("basic");
  const [task, setTask] = useState<FinanceTask>("summarize");
  const [providerId, setProviderId] = useState("finance-base");
  const [savedEntry, setSavedEntry] = useState<HistoryEntry | null>(null);

  const [showDashboardStatus, setShowDashboardStatus] = useState(false);
  const [showWorkflowMenu, setShowWorkflowMenu] = useState(false);

  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [ready, setReady] = useState<BackendReady | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [backendLoading, setBackendLoading] = useState(false);

  useEffect(() => {
    const storedAuth = loadAuth();
    setAuth(storedAuth);
  }, []);

  useEffect(() => {
    if (mode === "basic" && providerId !== "finance-base") {
      const selectedProvider = getProviderById(providerId);

      if (selectedProvider.tier !== "basic") {
        setProviderId("finance-base");
      }
    }

    if (mode === "premium" && providerId === "finance-base") {
      setProviderId("finance-adapter");
    }
  }, [mode, providerId]);

  async function refreshBackendStatus() {
    setBackendLoading(true);
    setBackendError(null);

    try {
      const [healthResponse, readyResponse] = await Promise.all([
        fetch("/api/backend/health", {
          cache: "no-store",
        }),
        fetch("/api/backend/ready", {
          cache: "no-store",
        }),
      ]);

      if (!healthResponse.ok) {
        throw new Error(`/health returned ${healthResponse.status}`);
      }

      if (!readyResponse.ok) {
        throw new Error(`/ready returned ${readyResponse.status}`);
      }

      const healthPayload = (await healthResponse.json()) as BackendHealth;
      const readyPayload = (await readyResponse.json()) as BackendReady;

      setHealth(healthPayload);
      setReady(readyPayload);
    } catch (error) {
      setHealth(null);
      setReady(null);
      setBackendError(
        error instanceof Error ? error.message : "Backend status check failed",
      );
    } finally {
      setBackendLoading(false);
    }
  }

  useEffect(() => {
    void refreshBackendStatus();

    const intervalId = window.setInterval(() => {
      void refreshBackendStatus();
    }, 5 * 60 * 1000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  function handleProviderSelect(nextProviderId: string) {
    const nextProvider = getProviderById(nextProviderId);

    setProviderId(nextProvider.id);
    setMode(nextProvider.tier === "basic" ? "basic" : "premium");
    setShowWorkflowMenu(false);
  }

  const provider = getProviderById(providerId);
  const displayName = getDisplayName(auth);
  const hasApiKey = Boolean(auth?.accessToken || defaultApiKey);
  const backendConnected = health?.status === "ok";
  const modelId = ready?.model_id ?? health?.model_id ?? provider.modelId;
  const lastUsage = savedEntry?.usage;

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar displayName={displayName} mode={mode} onLogout={handleLogout} />

        <AppTopMenu />

        <div className="mx-auto w-full max-w-7xl space-y-4 px-3 pb-8">
          <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-xl shadow-black/20">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs uppercase tracking-[0.24em] text-cyan-200/70">
                  Chat Workspace
                </p>

                <h1 className="mt-2 text-2xl font-semibold text-white">
                  Run finance LLM workflows
                </h1>

                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Route finance prompts to Basic or Premium models, attach
                  document context, and run summarization, Q&A, or risk analysis
                  from one workspace.
                </p>

                <div className="mt-3 flex flex-wrap gap-2">
                  <StatusPill label={modeLabel(mode)} tone="neutral" />
                  <StatusPill label={taskLabel(task)} tone="neutral" />
                  <StatusPill
                    label={provider.enabled ? "enabled" : "disabled"}
                    tone={provider.enabled ? "good" : "warn"}
                  />
                  <StatusPill
                    label={backendConnected ? "backend ok" : "backend offline"}
                    tone={backendConnected ? "good" : "warn"}
                  />
                </div>
              </div>

              <div className="flex shrink-0 flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setShowDashboardStatus((value) => !value)}
                  className={[
                    "rounded-xl border px-4 py-2.5 text-sm font-semibold transition",
                    showDashboardStatus
                      ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100"
                      : "border-white/10 bg-white/5 text-slate-200 hover:border-cyan-300/40 hover:bg-cyan-300/10",
                  ].join(" ")}
                >
                  {showDashboardStatus ? "Hide status" : "Status"}
                </button>

                <div className="relative">
                  <button
                    type="button"
                    onClick={() => setShowWorkflowMenu((value) => !value)}
                    className={[
                      "min-w-[220px] rounded-xl border px-4 py-2.5 text-left text-sm font-semibold transition",
                      showWorkflowMenu
                        ? "border-cyan-300/40 bg-cyan-300/10 text-cyan-100"
                        : "border-white/10 bg-white/5 text-slate-200 hover:border-cyan-300/40 hover:bg-cyan-300/10",
                    ].join(" ")}
                  >
                    <span className="block text-[11px] uppercase tracking-[0.16em] text-slate-400">
                      Workflow / Model
                    </span>
                    <span className="mt-1 block truncate">
                      {getProviderRouteLabel(provider)} · {provider.name}
                    </span>
                  </button>

                  {showWorkflowMenu ? (
                    <div className="absolute right-0 z-30 mt-3 w-[min(92vw,420px)] overflow-hidden rounded-3xl border border-white/10 bg-slate-950/95 p-3 shadow-2xl shadow-black/60 backdrop-blur-xl">
                      <div className="mb-2 flex items-center justify-between px-2">
                        <p className="text-xs uppercase tracking-[0.22em] text-cyan-200/70">
                          Select LLM
                        </p>
                        <button
                          type="button"
                          onClick={() => setShowWorkflowMenu(false)}
                          className="text-xs font-semibold text-slate-400 transition hover:text-white"
                        >
                          Close
                        </button>
                      </div>

                      <div className="max-h-[420px] space-y-2 overflow-y-auto pr-1">
                        {providerCatalog.map((item) => {
                          const isSelected = item.id === providerId;

                          return (
                            <button
                              key={item.id}
                              type="button"
                              onClick={() => handleProviderSelect(item.id)}
                              className={[
                                "w-full rounded-2xl border px-3 py-3 text-left transition",
                                isSelected
                                  ? "border-cyan-300/40 bg-cyan-300/10"
                                  : "border-white/10 bg-white/5 hover:border-white/20 hover:bg-white/10",
                              ].join(" ")}
                            >
                              <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                  <p className="truncate text-sm font-semibold text-white">
                                    {item.name}
                                  </p>
                                  <p className="mt-1 truncate text-xs text-slate-400">
                                    {item.provider} · {item.modelId}
                                  </p>
                                </div>

                                <span className="shrink-0 rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-slate-300">
                                  {getProviderRouteLabel(item)}
                                </span>
                              </div>

                              <p className="mt-2 text-xs leading-5 text-slate-400">
                                {item.description}
                              </p>

                              <div className="mt-3 flex flex-wrap gap-2">
                                <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-slate-400">
                                  {item.costClass}
                                </span>
                                <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-slate-400">
                                  {item.privacy}
                                </span>
                                <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-slate-400">
                                  {item.latency}
                                </span>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div className="min-w-0">
                <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">
                  Current Workflow
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-white">
                    {mode} · {task} · {provider.name}
                  </span>
                  <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-slate-300">
                    {provider.modelId}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <StatusPill
                  label={provider.enabled ? "enabled" : "disabled"}
                  tone={provider.enabled ? "good" : "warn"}
                />
                <StatusPill label={provider.costClass} tone="neutral" />
                <StatusPill label={provider.privacy} tone="neutral" />
                <StatusPill label={provider.latency} tone="neutral" />
              </div>
            </div>
          </section>

          {showDashboardStatus ? (
            <section className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
              <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-[0.2em] text-cyan-200/70">
                    Runtime Status
                  </p>
                  <h2 className="mt-2 text-lg font-semibold text-white">
                    Finance LLM control center
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-slate-400">
                    Backend readiness, current provider, session state, and
                    latest inference metadata.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={refreshBackendStatus}
                  disabled={backendLoading}
                  className="rounded-xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-2.5 text-sm font-semibold text-cyan-100 transition hover:bg-cyan-300/20 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {backendLoading ? "Refreshing..." : "Refresh backend"}
                </button>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                <InfoCard title="Backend">
                  <InfoRow label="API URL" value={apiBaseUrl} />
                  <InfoRow
                    label="/health"
                    value={
                      backendError ? (
                        <StatusPill label="error" tone="bad" />
                      ) : backendConnected ? (
                        <StatusPill label="ok" tone="good" />
                      ) : backendLoading ? (
                        <StatusPill label="checking" tone="warn" />
                      ) : (
                        <StatusPill label="unknown" tone="neutral" />
                      )
                    }
                  />
                  <InfoRow
                    label="/ready"
                    value={
                      ready?.ready ? (
                        <StatusPill label="ready" tone="good" />
                      ) : ready ? (
                        <StatusPill label="not ready" tone="warn" />
                      ) : backendError ? (
                        <StatusPill label="offline" tone="bad" />
                      ) : (
                        <StatusPill label="unknown" tone="neutral" />
                      )
                    }
                  />
                  {backendError ? (
                    <InfoRow label="Error" value={backendError} />
                  ) : null}
                </InfoCard>

                <InfoCard title="Configuration">
                  <InfoRow label="Mode" value={modeLabel(mode)} />
                  <InfoRow label="Task" value={taskLabel(task)} />
                  <InfoRow label="Provider" value={provider.name} />
                </InfoCard>

                <InfoCard title="Model">
                  <InfoRow label="Model ID" value={modelId} />
                  <InfoRow
                    label="Model loaded"
                    value={
                      ready?.model_loaded ? (
                        <StatusPill label="true" tone="good" />
                      ) : ready ? (
                        <StatusPill label="false" tone="warn" />
                      ) : (
                        <StatusPill label="unknown" tone="neutral" />
                      )
                    }
                  />
                  <InfoRow
                    label="Adapter loaded"
                    value={
                      ready?.adapter_loaded ? (
                        <StatusPill label="true" tone="good" />
                      ) : ready ? (
                        <StatusPill label="false" tone="warn" />
                      ) : (
                        <StatusPill label="unknown" tone="neutral" />
                      )
                    }
                  />
                </InfoCard>

                <InfoCard title="Session">
                  <InfoRow label="User" value={displayName} />
                  <InfoRow
                    label="API token"
                    value={
                      hasApiKey ? (
                        <StatusPill label="present" tone="good" />
                      ) : (
                        <StatusPill label="missing" tone="bad" />
                      )
                    }
                  />
                </InfoCard>

                <InfoCard title="Last run">
                  <InfoRow
                    label="Output"
                    value={
                      savedEntry ? (
                        <StatusPill label="saved" tone="good" />
                      ) : (
                        <StatusPill label="waiting" tone="neutral" />
                      )
                    }
                  />
                  <InfoRow label="Task" value={savedEntry?.task ?? "None yet"} />
                  <InfoRow
                    label="Latency/tokens"
                    value={
                      lastUsage
                        ? `${lastUsage.latencyMs} ms / ${lastUsage.totalTokens} tokens`
                        : "Not available"
                    }
                  />
                </InfoCard>

                <InfoCard title="Quick actions">
                  <div className="grid gap-2">
                    <button
                      type="button"
                      onClick={() => router.push("/compare")}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-left text-sm font-semibold text-white transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
                    >
                      Compare models
                      <span className="mt-1 block text-xs font-normal text-slate-400">
                        Run two providers side by side.
                      </span>
                    </button>

                    <button
                      type="button"
                      onClick={() => router.push("/history")}
                      className="rounded-xl border border-white/10 bg-white/5 px-3 py-2.5 text-left text-sm font-semibold text-white transition hover:border-cyan-300/40 hover:bg-cyan-300/10"
                    >
                      View history
                      <span className="mt-1 block text-xs font-normal text-slate-400">
                        Review saved inference outputs.
                      </span>
                    </button>
                  </div>
                </InfoCard>
              </div>
            </section>
          ) : null}

          <section className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
            <ChatPanel
              auth={auth}
              mode={mode}
              task={task}
              provider={provider}
              onModeChange={(nextMode) => setMode(nextMode)}
              onTaskChange={setTask}
              onProviderChange={setProviderId}
              onSaved={setSavedEntry}
            />
          </section>
        </div>
      </div>
    </main>
  );
}