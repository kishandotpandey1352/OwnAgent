"use client";

import { useState } from "react";

import { ResponseCard } from "@/components/ResponseCard";
import { runComparison } from "@/lib/api";
import { appendHistory } from "@/lib/history";
import type {
  AuthState,
  ComparisonResult,
  FinanceTask,
  HistoryEntry,
  ProviderOption,
} from "@/types";

interface ComparePanelProps {
  auth: AuthState | null;
  task: FinanceTask;
  providers: ProviderOption[];
  leftProvider: ProviderOption;
  rightProvider: ProviderOption;
  onLeftProviderChange: (providerId: string) => void;
  onRightProviderChange: (providerId: string) => void;
  onTaskChange: (task: FinanceTask) => void;
  onSaved?: (entry: HistoryEntry) => void;
}

function toHistoryEntry(
  response: ComparisonResult["left"],
  context?: string,
): HistoryEntry {
  return {
    ...response,
    sourcePrompt: response.prompt,
    context,
  };
}

function getTaskLabel(task: FinanceTask) {
  if (task === "summarize") return "Summarize";
  if (task === "qa") return "Q&A";
  return "Risk Analysis";
}

function getProviderRouteLabel(provider: ProviderOption) {
  return provider.tier === "basic" ? "Basic" : "Premium";
}

function MiniPill({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: "cyan" | "emerald" | "violet" | "amber" | "slate";
}) {
  const toneClass =
    tone === "cyan"
      ? "border-cyan-300/20 bg-cyan-300/10 text-cyan-100"
      : tone === "emerald"
        ? "border-emerald-300/20 bg-emerald-300/10 text-emerald-100"
        : tone === "violet"
          ? "border-violet-300/20 bg-violet-300/10 text-violet-100"
          : tone === "amber"
            ? "border-amber-300/20 bg-amber-300/10 text-amber-100"
            : "border-white/10 bg-white/5 text-slate-300";

  return (
    <span
      className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-semibold ${toneClass}`}
    >
      {children}
    </span>
  );
}

function ProviderSummary({
  label,
  provider,
  tone,
}: {
  label: string;
  provider: ProviderOption;
  tone: "cyan" | "emerald";
}) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
            {label}
          </p>
          <p className="mt-1 truncate text-sm font-semibold text-white">
            {provider.name}
          </p>
          <p className="mt-1 truncate text-xs text-slate-400">
            {provider.provider} · {provider.modelId}
          </p>
        </div>

        <MiniPill tone={tone}>{getProviderRouteLabel(provider)}</MiniPill>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <MiniPill>{provider.costClass}</MiniPill>
        <MiniPill>{provider.privacy}</MiniPill>
        <MiniPill>{provider.latency}</MiniPill>
      </div>
    </div>
  );
}

export function ComparePanel({
  auth,
  task,
  providers,
  leftProvider,
  rightProvider,
  onLeftProviderChange,
  onRightProviderChange,
  onTaskChange,
  onSaved,
}: ComparePanelProps) {
  const [prompt, setPrompt] = useState(
    "Compare the risks and outlook in the following company excerpt.",
  );
  const [context, setContext] = useState(
    "Operating cash flow improved, but debt costs remain elevated and management signaled a cautious outlook.",
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComparisonResult | null>(null);

  async function handleCompare() {
    if (!prompt.trim()) {
      setError("Add a prompt before comparing providers.");
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const comparison = await runComparison({
        prompt: prompt.trim(),
        context: context.trim() || undefined,
        leftProvider,
        rightProvider,
        task,
        accessToken: auth?.accessToken,
      });

      setResult(comparison);

      const leftEntry = toHistoryEntry(
        comparison.left,
        context.trim() || undefined,
      );
      const rightEntry = toHistoryEntry(
        comparison.right,
        context.trim() || undefined,
      );

      appendHistory(leftEntry);
      appendHistory(rightEntry);
      onSaved?.(leftEntry);
      onSaved?.(rightEntry);
    } catch (compareError) {
      setError(
        compareError instanceof Error
          ? compareError.message
          : "Comparison failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-violet-200/70">
                Prompt Composer
              </p>
              <h2 className="mt-2 text-lg font-semibold text-white">
                Shared evaluation prompt
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-400">
                This prompt and context will be sent to both selected providers.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <MiniPill tone="violet">{getTaskLabel(task)}</MiniPill>
              <MiniPill>Same input</MiniPill>
            </div>
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <label className="block space-y-2">
              <span className="text-sm font-semibold text-slate-200">
                Prompt
              </span>
              <textarea
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                rows={5}
                className="min-h-[170px] w-full rounded-2xl border border-white/10 bg-black/25 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-500 focus:border-violet-300/50 focus:ring-2 focus:ring-violet-400/20"
                placeholder="Ask both models to compare financial risks, outlook, assumptions, or key drivers..."
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-semibold text-slate-200">
                Context
              </span>
              <textarea
                value={context}
                onChange={(event) => setContext(event.target.value)}
                rows={5}
                className="min-h-[170px] w-full rounded-2xl border border-white/10 bg-black/25 px-3 py-3 text-sm leading-6 text-white outline-none transition placeholder:text-slate-500 focus:border-violet-300/50 focus:ring-2 focus:ring-violet-400/20"
                placeholder="Paste the company excerpt, financial update, or disclosure context..."
              />
            </label>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
            <p className="text-xs uppercase tracking-[0.2em] text-violet-200/70">
              Provider Setup
            </p>
            <h2 className="mt-2 text-lg font-semibold text-white">
              Model pair
            </h2>

            <div className="mt-4 space-y-3">
              <label className="block space-y-1.5">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Left provider
                </span>
                <select
                  value={leftProvider.id}
                  onChange={(event) =>
                    onLeftProviderChange(event.target.value)
                  }
                  className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none transition focus:border-cyan-300/40"
                >
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.provider} · {provider.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block space-y-1.5">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">
                  Right provider
                </span>
                <select
                  value={rightProvider.id}
                  onChange={(event) =>
                    onRightProviderChange(event.target.value)
                  }
                  className="w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2.5 text-sm text-white outline-none transition focus:border-emerald-300/40"
                >
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {provider.provider} · {provider.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 grid gap-3">
              <ProviderSummary
                label="Left"
                provider={leftProvider}
                tone="cyan"
              />
              <ProviderSummary
                label="Right"
                provider={rightProvider}
                tone="emerald"
              />
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-500">
              Evaluation Task
            </p>

            <div className="mt-3 flex flex-wrap gap-2">
              {(["summarize", "qa", "risk-analysis"] as FinanceTask[]).map(
                (item) => {
                  const isActive = task === item;

                  return (
                    <button
                      key={item}
                      type="button"
                      onClick={() => onTaskChange(item)}
                      className={[
                        "rounded-xl border px-3 py-2 text-xs font-semibold transition",
                        isActive
                          ? "border-violet-300/40 bg-violet-300/10 text-violet-50"
                          : "border-white/10 bg-white/0 text-slate-300 hover:border-white/20 hover:bg-white/5",
                      ].join(" ")}
                    >
                      {getTaskLabel(item)}
                    </button>
                  );
                },
              )}
            </div>

            <button
              type="button"
              onClick={() => void handleCompare()}
              disabled={loading}
              className="mt-4 w-full rounded-xl bg-gradient-to-r from-violet-300 to-cyan-300 px-4 py-2.5 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? "Comparing..." : "Run comparison"}
            </button>

            {error ? (
              <p className="mt-3 rounded-xl border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm leading-6 text-rose-100">
                {error}
              </p>
            ) : null}
          </div>
        </aside>
      </div>

      <section className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-violet-200/70">
              Comparison Result
            </p>
            <h3 className="mt-2 text-lg font-semibold text-white">
              Side-by-side model outputs
            </h3>
            <p className="mt-1 text-sm leading-6 text-slate-400">
              Review response quality, structure, latency, and metadata from
              both providers.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <MiniPill tone="cyan">{leftProvider.name}</MiniPill>
            <MiniPill>vs</MiniPill>
            <MiniPill tone="emerald">{rightProvider.name}</MiniPill>
          </div>
        </div>

        {result ? (
          <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="min-w-0 [&>*]:h-full">
              <ResponseCard
                response={result.left}
                accent="from-cyan-400/40 to-sky-500/20"
              />
            </div>

            <div className="min-w-0 [&>*]:h-full">
              <ResponseCard
                response={result.right}
                accent="from-emerald-400/30 to-violet-400/20"
              />
            </div>
          </div>
        ) : (
          <div className="mt-4 rounded-2xl border border-dashed border-white/15 bg-black/20 p-6 text-center">
            <p className="text-sm font-medium text-slate-300">
              Run a comparison to see both outputs side by side.
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-500">
              The result panel will show both provider responses with metadata.
            </p>
          </div>
        )}
      </section>
    </section>
  );
}