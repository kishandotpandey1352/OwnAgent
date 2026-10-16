import type { UsageMetadata } from "@/types";

interface UsageBadgeProps {
  usage: UsageMetadata;
  compact?: boolean;
}

function formatLatency(latencyMs: number) {
  if (latencyMs < 1000) {
    return `${latencyMs} ms`;
  }

  return `${(latencyMs / 1000).toFixed(1)} s`;
}

export function UsageBadge({ usage, compact = false }: UsageBadgeProps) {
  return (
    <div className={`grid gap-2 rounded-2xl border border-white/10 bg-white/5 p-4 text-xs text-slate-200 ${compact ? "sm:grid-cols-2" : "md:grid-cols-4"}`}>
      <div>
        <p className="uppercase tracking-[0.2em] text-slate-400">Provider</p>
        <p className="mt-1 text-sm font-medium text-white">{usage.provider}</p>
      </div>
      <div>
        <p className="uppercase tracking-[0.2em] text-slate-400">Model</p>
        <p className="mt-1 text-sm font-medium text-white">{usage.modelId}</p>
      </div>
      <div>
        <p className="uppercase tracking-[0.2em] text-slate-400">Tokens</p>
        <p className="mt-1 text-sm font-medium text-white">{usage.totalTokens.toLocaleString()} total</p>
      </div>
      <div>
        <p className="uppercase tracking-[0.2em] text-slate-400">Latency</p>
        <p className="mt-1 text-sm font-medium text-white">{formatLatency(usage.latencyMs)}</p>
      </div>
      <div className="sm:col-span-2 md:col-span-4">
        <p className="uppercase tracking-[0.2em] text-slate-400">Mode / task</p>
        <p className="mt-1 text-sm font-medium text-white">
          {usage.task} · {usage.source}
        </p>
      </div>
    </div>
  );
}