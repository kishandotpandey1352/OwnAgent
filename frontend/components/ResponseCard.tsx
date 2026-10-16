import type { ReactNode } from "react";

import { CitedAnswer } from "@/components/CitedAnswer";
import { UsageBadge } from "@/components/UsageBadge";
import type { WebAwareFinanceResponse } from "@/lib/api";

interface ResponseCardProps {
  response: WebAwareFinanceResponse;
  accent?: string;
  footer?: ReactNode;
}

export function ResponseCard({ response, accent = "from-cyan-400/30 to-sky-500/10", footer }: ResponseCardProps) {
  return (
    <article className="overflow-hidden rounded-[28px] border border-white/10 bg-panel/90 shadow-halo backdrop-blur">
      <div className={`h-1 bg-gradient-to-r ${accent}`} />
      <div className="space-y-5 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{response.title}</p>
            <h3 className="mt-1 text-xl font-semibold text-white">{response.provider}</h3>
            <p className="mt-1 text-sm text-slate-400">{response.modelId}</p>
          </div>
          <div className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-slate-200">
            {response.mode} · {response.task}
          </div>
        </div>

        <div className="rounded-3xl border border-white/8 bg-black/20 p-4 text-sm leading-7 text-slate-100">
          <CitedAnswer
            text={response.output}
            citations={response.web_research?.citations ?? []}
          />
        </div>

        <UsageBadge usage={response.usage} compact />

        {footer}

        <p className="text-xs text-slate-500">Captured {new Date(response.createdAt).toLocaleString()}</p>
      </div>
    </article>
  );
}