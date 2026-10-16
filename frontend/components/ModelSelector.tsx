"use client";

import { useEffect, useMemo } from "react";

import type { AppMode, FinanceTask, ProviderOption } from "@/types";
import { comparisonPairs, tasks } from "@/lib/models";

interface ModelSelectorProps {
  mode: AppMode;
  task: FinanceTask;
  providerId: string;
  comparisonProviderId?: string;
  onModeChange: (mode: AppMode) => void;
  onTaskChange: (task: FinanceTask) => void;
  onProviderChange: (providerId: string) => void;
  onComparisonProviderChange?: (providerId: string) => void;
  providers: ProviderOption[];
}

function getProviderLabel(provider: ProviderOption["provider"]) {
  const labels: Record<ProviderOption["provider"], string> = {
    "finance-eks": "Finance EKS",
    openai: "OpenAI",
    anthropic: "Anthropic",
    gemini: "Gemini",
    bedrock: "Amazon Bedrock",
    vllm: "vLLM",
    ollama: "Ollama",
  };

  return labels[provider];
}

function getModeDescription(mode: AppMode) {
  if (mode === "basic") {
    return "Low-cost daily usage with the self-hosted finance model.";
  }

  if (mode === "premium") {
    return "Route to stronger paid, AWS-managed, or self-hosted premium providers.";
  }

  return "Run side-by-side inference comparison across two providers.";
}

function getProvidersForMode(mode: AppMode, providers: ProviderOption[]) {
  const enabledProviders = providers.filter((provider) => provider.enabled);

  if (mode === "basic") {
    return enabledProviders.filter((provider) => provider.tier === "basic");
  }

  if (mode === "premium") {
    return enabledProviders.filter(
      (provider) =>
        provider.tier === "premium" || provider.provider === "finance-eks",
    );
  }

  return enabledProviders;
}

export function ModelSelector({
  mode,
  task,
  providerId,
  comparisonProviderId,
  onModeChange,
  onTaskChange,
  onProviderChange,
  onComparisonProviderChange,
  providers,
}: ModelSelectorProps) {
  const availableProviders = useMemo(
    () => getProvidersForMode(mode, providers),
    [mode, providers],
  );

  const comparisonProviders = useMemo(
    () => providers.filter((provider) => provider.enabled),
    [providers],
  );

  const activeProvider =
    availableProviders.find((provider) => provider.id === providerId) ??
    availableProviders[0] ??
    providers[0];

  const activeComparisonProvider =
    comparisonProviders.find((provider) => provider.id === comparisonProviderId) ??
    comparisonProviders.find((provider) => provider.id !== activeProvider?.id) ??
    comparisonProviders[0] ??
    activeProvider;

  useEffect(() => {
    if (!activeProvider) {
      return;
    }

    const isProviderValidForMode = availableProviders.some(
      (provider) => provider.id === providerId,
    );

    if (!isProviderValidForMode) {
      onProviderChange(activeProvider.id);
    }
  }, [activeProvider, availableProviders, providerId, onProviderChange]);

  useEffect(() => {
    if (
      mode !== "compare" ||
      !onComparisonProviderChange ||
      !activeComparisonProvider
    ) {
      return;
    }

    const isComparisonProviderValid = comparisonProviders.some(
      (provider) => provider.id === comparisonProviderId,
    );

    if (!isComparisonProviderValid) {
      onComparisonProviderChange(activeComparisonProvider.id);
    }
  }, [
    mode,
    comparisonProviderId,
    comparisonProviders,
    activeComparisonProvider,
    onComparisonProviderChange,
  ]);

  return (
    <section className="space-y-5 rounded-[32px] border border-white/10 bg-panel/85 p-6 shadow-halo backdrop-blur-xl">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">
            Workflow
          </p>
          <h2 className="mt-2 text-3xl font-semibold text-white">
            Choose the mode, task, and provider
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">
            Select the operating mode, finance task type, and provider route
            before running the configured request in Chat Workspace.
          </p>
        </div>

        {activeProvider ? (
          <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs tracking-[0.18em] text-slate-300">
            {activeProvider.name}
          </div>
        ) : null}
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {(["basic", "premium", "compare"] as AppMode[]).map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onModeChange(item)}
            className={[
              "rounded-2xl border px-4 py-3 text-left transition",
              mode === item
                ? "border-cyan-300/40 bg-cyan-300/10 text-white"
                : "border-white/10 bg-black/10 text-slate-300 hover:border-white/20 hover:bg-white/5",
            ].join(" ")}
          >
            <p className="text-sm font-semibold capitalize">{item}</p>
            <p className="mt-1 text-xs text-slate-400">
              {getModeDescription(item)}
            </p>
          </button>
        ))}
      </div>

      <div className="space-y-4 rounded-3xl border border-white/10 bg-black/15 p-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
              Task
            </p>
            <p className="text-sm text-slate-300">
              The backend routes to summarize, Q&A, or risk analysis endpoints.
            </p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          {tasks.map((item) => (
            <button
              key={item.value}
              type="button"
              onClick={() => onTaskChange(item.value)}
              className={[
                "rounded-2xl border px-4 py-4 text-left transition",
                task === item.value
                  ? "border-cyan-300/40 bg-cyan-300/10 text-white"
                  : "border-white/10 bg-white/0 text-slate-300 hover:border-white/20 hover:bg-white/5",
              ].join(" ")}
            >
              <p className="font-semibold">{item.label}</p>
              <p className="mt-1 text-xs text-slate-400">
                {item.description}
              </p>
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-4 rounded-3xl border border-white/10 bg-black/15 p-4">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
            Provider
          </p>
          <p className="mt-1 text-sm text-slate-300">
            {mode === "basic"
              ? "Basic mode uses the self-hosted finance model."
              : mode === "premium"
                ? "Premium mode can route to EKS, paid APIs, AWS-managed models, or open-source providers."
                : "Compare mode lets you select two providers for side-by-side evaluation."}
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {availableProviders.map((providerOption) => {
            const isSelected = providerId === providerOption.id;

            return (
              <button
                key={providerOption.id}
                type="button"
                onClick={() => onProviderChange(providerOption.id)}
                className={[
                  "rounded-2xl border p-4 text-left transition",
                  isSelected
                    ? "border-cyan-300/50 bg-cyan-300/10 text-white shadow-halo"
                    : "border-white/10 bg-white/[0.03] text-slate-300 hover:border-white/25 hover:bg-white/[0.06]",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-white">
                      {providerOption.name}
                    </p>
                    <p className="mt-1 text-xs text-cyan-100/70">
                      {getProviderLabel(providerOption.provider)}
                    </p>
                  </div>

                  <span className="rounded-full border border-white/10 bg-black/20 px-2 py-1 text-[10px] uppercase tracking-wide text-slate-300">
                    {providerOption.tier}
                  </span>
                </div>

                <p className="mt-3 text-xs leading-6 text-slate-400">
                  {providerOption.description}
                </p>

                <div className="mt-4 grid gap-2 text-xs text-slate-400">
                  <div className="flex justify-between gap-3">
                    <span>Model</span>
                    <span className="max-w-[12rem] truncate text-right text-slate-200">
                      {providerOption.modelId}
                    </span>
                  </div>

                  <div className="flex justify-between gap-3">
                    <span>Cost</span>
                    <span className="text-right text-slate-200">
                      {providerOption.costClass}
                    </span>
                  </div>

                  <div className="flex justify-between gap-3">
                    <span>Privacy</span>
                    <span className="text-right text-slate-200">
                      {providerOption.privacy}
                    </span>
                  </div>

                  <div className="flex justify-between gap-3">
                    <span>Latency</span>
                    <span className="text-right text-slate-200">
                      {providerOption.latency}
                    </span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {mode === "compare" && onComparisonProviderChange ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-slate-400">
                  Comparison provider
                </p>
                <select
                  value={comparisonProviderId ?? activeComparisonProvider?.id}
                  onChange={(event) =>
                    onComparisonProviderChange(event.target.value)
                  }
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-panel/95 px-4 py-3 text-sm text-white outline-none focus:border-cyan-300/50"
                >
                  {comparisonProviders.map((provider) => (
                    <option key={provider.id} value={provider.id}>
                      {getProviderLabel(provider.provider)} · {provider.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                  Preset
                </p>
                <p className="mt-2 text-sm text-slate-300">
                  {comparisonPairs.find(
                    (pair) =>
                      pair.left === providerId &&
                      pair.right === comparisonProviderId,
                  )?.label ?? "Custom pair"}
                </p>
                <p className="mt-2 text-xs text-slate-500">
                  Current comparison: {activeProvider?.name ?? "None"} vs{" "}
                  {activeComparisonProvider?.name ?? "None"}
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}