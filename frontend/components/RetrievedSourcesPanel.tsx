"use client";

import { useEffect, useState } from "react";

export type RetrievedEvidenceSource = {
  documentId: string;
  chunkId: string;
  fileName: string;
  chunkIndex: number;
  pageNumber?: number;
  score: number;
  snippet: string;
};

interface RetrievedSourcesPanelProps {
  sources: RetrievedEvidenceSource[];
  defaultOpen?: boolean;
}

export function RetrievedSourcesPanel({
  sources,
  defaultOpen = true,
}: RetrievedSourcesPanelProps) {
  const [open, setOpen] = useState(defaultOpen);

  useEffect(() => {
    setOpen(defaultOpen);
  }, [defaultOpen, sources.length]);

  if (!sources.length) return null;

  return (
    <section className="overflow-hidden rounded-2xl border border-white/10 bg-slate-950/75 shadow-lg shadow-black/10">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-white/[0.03]"
      >
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-200/70">
              Retrieved document sources
            </p>
            <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-2 py-0.5 text-[10px] font-semibold text-amber-100">
              {sources.length} chunk{sources.length === 1 ? "" : "s"}
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Evidence retrieved from uploaded documents.
          </p>
        </div>
        <span className={`shrink-0 text-lg text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}>
          ▾
        </span>
      </button>

      {open ? (
        <div className="border-t border-white/10 p-3">
          <div className="space-y-2">
            {sources.map((source, index) => (
              <details key={source.chunkId} className="group rounded-xl border border-white/10 bg-black/20">
                <summary className="cursor-pointer list-none px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-xs font-semibold text-white">
                        Source {index + 1} · {source.fileName}
                      </p>
                      <p className="mt-1 text-[10px] text-slate-500">
                        Chunk {source.chunkIndex}
                        {source.pageNumber ? ` · page ${source.pageNumber}` : ""}
                        {" · score "}
                        {source.score.toFixed(3)}
                      </p>
                    </div>
                    <span className="shrink-0 text-sm text-slate-500 transition-transform group-open:rotate-180">▾</span>
                  </div>
                </summary>
                <div className="border-t border-white/10 px-3 pb-3 pt-2">
                  <p className="text-xs leading-5 text-slate-400">{source.snippet}</p>
                </div>
              </details>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
