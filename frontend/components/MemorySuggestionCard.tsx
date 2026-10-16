"use client";

import { useEffect } from "react";

type MemorySuggestion = {
  is_memory_request: boolean;
  memory_type: string | null;
  memory_key: string | null;
  memory_value: string | null;
  confidence: number;
  requires_confirmation: boolean;
  reason: string | null;
  blocked: boolean;
};

function formatMemoryType(value: string | null) {
  if (!value) return "Preference";

  return value
    .split("_")
    .map((word) => word.slice(0, 1).toUpperCase() + word.slice(1))
    .join(" ");
}

export function MemorySuggestionCard({
  suggestion,
  saving,
  onSave,
  onDismiss,
}: {
  suggestion: MemorySuggestion;
  saving: boolean;
  onSave: () => void;
  onDismiss: () => void;
}) {
  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  if (!suggestion.is_memory_request) return null;

  if (suggestion.blocked) {
    return (
      <div
        className="fixed inset-0 z-[80] flex items-center justify-center bg-black/75 px-4 py-6 backdrop-blur-md"
        role="dialog"
        aria-modal="true"
        aria-labelledby="blocked-memory-title"
      >
        <div className="w-full max-w-xl rounded-3xl border border-amber-300/25 bg-slate-950 p-5 shadow-2xl shadow-black/60">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-amber-300/25 bg-amber-300/10 text-xl">
            ⚠️
          </div>

          <div className="mt-4 text-center">
            <p className="text-xs uppercase tracking-[0.24em] text-amber-200/80">
              Memory blocked
            </p>

            <h2
              id="blocked-memory-title"
              className="mt-2 text-xl font-semibold text-white"
            >
              This should not be saved as memory
            </h2>

            <p className="mt-3 text-sm leading-6 text-slate-300">
              {suggestion.reason ??
                "This looks like sensitive personal or financial information, so it should not be stored as long-term memory."}
            </p>
          </div>

          <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
              Why?
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              Your app should remember preferences like answer style, chart
              style, or risk tone. It should not remember private financial
              facts such as holdings, income, debt, account details, or
              portfolio information.
            </p>
          </div>

          <div className="mt-5 flex justify-center">
            <button
              type="button"
              onClick={onDismiss}
              className="rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-slate-100 transition hover:bg-white/10"
            >
              I understand
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/75 px-4 py-6 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-labelledby="save-memory-title"
    >
      <div className="w-full max-w-xl rounded-3xl border border-cyan-300/25 bg-slate-950 p-5 shadow-2xl shadow-black/60">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-300/25 bg-cyan-300/10 text-xl">
          🧠
        </div>

        <div className="mt-4 text-center">
          <p className="text-xs uppercase tracking-[0.24em] text-cyan-200/80">
            Save memory?
          </p>

          <h2
            id="save-memory-title"
            className="mt-2 text-xl font-semibold text-white"
          >
            I detected a preference you may want me to remember
          </h2>

          <p className="mt-3 text-sm leading-6 text-slate-300">
            This will only be saved if you approve it. Saved memory affects
            answer style, tone, workflow, and formatting only — not financial
            facts.
          </p>
        </div>

        <div className="mt-5 rounded-2xl border border-cyan-300/20 bg-cyan-300/10 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2.5 py-1 text-[11px] font-semibold text-cyan-100">
              {formatMemoryType(suggestion.memory_type)}
            </span>

            {suggestion.memory_key ? (
              <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] font-semibold text-slate-300">
                {suggestion.memory_key}
              </span>
            ) : null}
          </div>

          <p className="mt-3 text-sm font-semibold leading-6 text-white">
            {suggestion.memory_value}
          </p>
        </div>

        <div className="mt-5 rounded-2xl border border-white/10 bg-black/25 p-4">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
            What happens if you save?
          </p>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Future agent answers can use this preference. You can delete it
            later from the top-right Settings menu under Memory preferences.
          </p>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={onDismiss}
            disabled={saving}
            className="rounded-xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-slate-100 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Don’t save
          </button>

          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="rounded-xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save memory"}
          </button>
        </div>
      </div>
    </div>
  );
}