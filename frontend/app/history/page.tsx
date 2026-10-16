"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ResponseCard } from "@/components/ResponseCard";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { clearHistory, loadHistory } from "@/lib/history";
import type { AuthState, HistoryEntry } from "@/types";
import { AppTopMenu } from "@/components/AppTopMenu";

function formatFileSize(size: number) {
  if (size < 1024) {
    return `${size} B`;
  }

  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }

  return `${(size / 1024 / 1024).toFixed(1)} MB`;
}

function getAttachmentLabel(kind: string) {
  if (kind === "pdf") return "PDF";
  if (kind === "docx") return "DOCX";
  if (kind === "text") return "TEXT";
  if (kind === "csv") return "CSV";
  if (kind === "image") return "IMAGE";
  return kind.toUpperCase();
}

function getTaskLabel(task?: string) {
  if (task === "qa") return "Q&A";
  if (task === "risk-analysis") return "Risk Analysis";
  if (task === "summarize") return "Summarize";
  return task ?? "Run";
}

function formatDate(value?: string) {
  if (!value) return "Unknown time";

  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function MiniPill({
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

function FilesUsedPanel({ entry }: { entry: HistoryEntry }) {
  const attachments = entry.attachments ?? [];

  if (!attachments.length) {
    return (
      <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
        <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
          Files used
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          No attached files were used for this run.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-emerald-300/20 bg-emerald-300/10 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-emerald-100/70">
            Files used
          </p>
          <p className="mt-1 text-xs text-slate-300">
            {attachments.length} attachment
            {attachments.length === 1 ? "" : "s"} included.
          </p>
        </div>

        <MiniPill tone="emerald">Document-aware</MiniPill>
      </div>

      <div className="mt-3 space-y-2">
        {attachments.map((attachment) => (
          <div
            key={attachment.id}
            className="rounded-xl border border-white/10 bg-black/25 px-3 py-2"
            title={`${attachment.name} · ${attachment.type}`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-white">
                  {attachment.name}
                </p>
                <p className="mt-1 text-[11px] text-slate-400">
                  {getAttachmentLabel(attachment.kind)} ·{" "}
                  {formatFileSize(attachment.size)}
                  {attachment.pageCount
                    ? ` · ${attachment.pageCount} pages`
                    : ""}
                </p>
              </div>

              <MiniPill>{getAttachmentLabel(attachment.kind)}</MiniPill>
            </div>

            <div className="mt-2 flex flex-wrap gap-2 text-[11px]">
              {typeof attachment.extractedChars === "number" ? (
                <MiniPill>
                  {attachment.extractedChars.toLocaleString()} chars
                </MiniPill>
              ) : null}

              {attachment.truncated ? (
                <MiniPill tone="amber">Truncated</MiniPill>
              ) : (
                <MiniPill tone="emerald">Full extract</MiniPill>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function HistoryMetadata({ entry }: { entry: HistoryEntry }) {
  const usage = entry.usage;

  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
        Run metadata
      </p>

      <div className="mt-3 space-y-2 text-xs">
        <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-2">
          <span className="text-slate-400">Task</span>
          <span className="font-semibold text-white">
            {getTaskLabel(entry.task)}
          </span>
        </div>

        <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-2">
          <span className="text-slate-400">Provider</span>
          <span className="max-w-[60%] truncate text-right font-semibold text-white">
            {entry.provider}
          </span>
        </div>

        <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-2">
          <span className="text-slate-400">Model</span>
          <span className="max-w-[60%] truncate text-right font-semibold text-white">
            {entry.modelId ?? "Unknown"}
          </span>
        </div>

        <div className="flex items-center justify-between gap-3 border-b border-white/5 pb-2">
          <span className="text-slate-400">Created</span>
          <span className="max-w-[60%] text-right font-semibold text-white">
            {formatDate(entry.createdAt)}
          </span>
        </div>

        <div className="flex items-center justify-between gap-3">
          <span className="text-slate-400">Usage</span>
          <span className="max-w-[60%] text-right font-semibold text-white">
            {usage
              ? `${usage.latencyMs} ms / ${usage.totalTokens} tokens`
              : "Not available"}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    setAuth(loadAuth());
    setHistory(loadHistory());
  }, []);

  function handleRefresh() {
    setHistory(loadHistory());
  }

  function handleClear() {
    const confirmed = window.confirm(
      "Clear all saved run history from this browser?",
    );

    if (!confirmed) return;

    clearHistory();
    setHistory([]);
  }

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  const totalAttachments = history.reduce(
    (count, entry) => count + (entry.attachments?.length ?? 0),
    0,
  );

  const latestRun = useMemo(() => history[0], [history]);

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar
          displayName={getDisplayName(auth)}
          mode="basic"
          onLogout={handleLogout}
        />
        
          <AppTopMenu />

        <div className="mx-auto w-full max-w-7xl space-y-4 px-3 pb-8">
          <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-xl shadow-black/20">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs uppercase tracking-[0.24em] text-emerald-200/70">
                  History
                </p>

                <h1 className="mt-2 text-2xl font-semibold text-white">
                  Recent finance AI runs
                </h1>

                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Review saved summaries, Q&A answers, risk analysis outputs,
                  comparison runs, and safe attachment metadata from this
                  browser.
                </p>

                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <MiniPill>{history.length} saved run{history.length === 1 ? "" : "s"}</MiniPill>
                  <MiniPill tone="emerald">
                    {totalAttachments} file reference
                    {totalAttachments === 1 ? "" : "s"}
                  </MiniPill>
                  <MiniPill tone={latestRun ? "cyan" : "slate"}>
                    Latest: {latestRun ? getTaskLabel(latestRun.task) : "None"}
                  </MiniPill>
                </div>
              </div>

              <div className="flex shrink-0 flex-wrap gap-3">
                <button
                  type="button"
                  onClick={handleRefresh}
                  className="rounded-xl border border-emerald-300/20 bg-emerald-300/10 px-4 py-2.5 text-sm font-semibold text-emerald-50 transition hover:border-emerald-200/40 hover:bg-emerald-300/20"
                >
                  Refresh
                </button>

                <button
                  type="button"
                  onClick={handleClear}
                  disabled={!history.length}
                  className="rounded-xl border border-white/10 bg-white/0 px-4 py-2.5 text-sm font-semibold text-slate-300 transition hover:border-rose-300/30 hover:bg-rose-300/10 hover:text-rose-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Clear history
                </button>
              </div>
            </div>
          </section>

          {history.length ? (
            <div className="space-y-4">
              {history.map((entry, index) => (
                <section
                  key={entry.id}
                  className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15"
                >
                  <div className="mb-4 flex flex-col gap-3 border-b border-white/10 pb-4 md:flex-row md:items-center md:justify-between">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="text-xs uppercase tracking-[0.2em] text-emerald-200/70">
                          Run {history.length - index}
                        </p>
                        <MiniPill tone="cyan">{getTaskLabel(entry.task)}</MiniPill>
                        {entry.attachments?.length ? (
                          <MiniPill tone="emerald">
                            {entry.attachments.length} file
                            {entry.attachments.length === 1 ? "" : "s"}
                          </MiniPill>
                        ) : null}
                      </div>

                      <h2 className="mt-2 truncate text-lg font-semibold text-white">
                        {entry.provider} · {entry.modelId ?? "Unknown model"}
                      </h2>

                      <p className="mt-1 text-sm text-slate-400">
                        {formatDate(entry.createdAt)}
                      </p>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      {entry.usage ? (
                        <>
                          <MiniPill>{entry.usage.latencyMs} ms</MiniPill>
                          <MiniPill>
                            {entry.usage.totalTokens} tokens
                          </MiniPill>
                        </>
                      ) : (
                        <MiniPill>Usage unavailable</MiniPill>
                      )}
                    </div>
                  </div>

                  <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
                    <aside className="space-y-3">
                      <HistoryMetadata entry={entry} />
                      <FilesUsedPanel entry={entry} />
                    </aside>

                    <div className="min-w-0">
                      <ResponseCard response={entry} />
                    </div>
                  </div>
                </section>
              ))}
            </div>
          ) : (
            <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-8 text-center shadow-xl shadow-black/15">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-500">
                No history yet
              </p>
              <h2 className="mt-2 text-xl font-semibold text-white">
                Saved runs will appear here
              </h2>
              <p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-slate-400">
                Generate a summary, Q&A answer, risk analysis, document-aware
                response, or model comparison and the saved output will appear
                in this history workspace.
              </p>

              <div className="mt-5 flex flex-wrap justify-center gap-3">
                <button
                  type="button"
                  onClick={() => router.push("/dashboard")}
                  className="rounded-xl bg-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200"
                >
                  Go to workspace
                </button>

                <button
                  type="button"
                  onClick={() => router.push("/compare")}
                  className="rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/10"
                >
                  Compare models
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}