"use client";

type WebFallbackToggleProps = {
  enabled: boolean;
  disabled?: boolean;
  onChange: (enabled: boolean) => void;
};

export function WebFallbackToggle({
  enabled,
  disabled = false,
  onChange,
}: WebFallbackToggleProps) {
  return (
    <div className="rounded-2xl border border-cyan-300/20 bg-cyan-300/[0.05] p-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-semibold text-white">
            Public web fallback
          </p>

          <p className="mt-1 text-xs leading-5 text-slate-400">
            Search trusted public web sources only when local
            documents and evidence are insufficient.
          </p>

          <p
            className={[
              "mt-2 text-xs font-semibold",
              enabled
                ? "text-cyan-200"
                : "text-slate-500",
            ].join(" ")}
          >
            {enabled
              ? "Web fallback enabled if needed"
              : "Web fallback is off"}
          </p>
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          disabled={disabled}
          onClick={() => {
            onChange(!enabled);
          }}
          className={[
            "relative inline-flex h-7 w-12 shrink-0 rounded-full",
            "border transition-all duration-200",
            "disabled:cursor-not-allowed disabled:opacity-50",

            enabled
              ? "border-cyan-300/50 bg-cyan-400"
              : "border-white/20 bg-slate-700",
          ].join(" ")}
        >
          <span
            className={[
              "absolute top-0.5 h-5 w-5 rounded-full bg-white",
              "shadow transition-all duration-200",

              enabled
                ? "left-6"
                : "left-1",
            ].join(" ")}
          />
        </button>
      </div>
    </div>
  );
}