"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { AppMode } from "@/types";

type SidebarProps = {
  displayName: string;
  mode: AppMode;
  onLogout: () => void;
};

const navItems = [
  {
    href: "/dashboard",
    label: "Workspace",
    description: "Chat",
    accent: "cyan",
  },
  {
    href: "/doc-search",
    label: "Doc Search",
    description: "RAG",
    accent: "lime",
  },
  {
  href: "/data",
  label: "Data Analysis",
  description: "CSV",
  accent: "amber",
  },
  {
    href: "/compare",
    label: "Compare",
    description: "Models",
    accent: "violet",
  },
  {
    href: "/history",
    label: "History",
    description: "Runs",
    accent: "emerald",
    },
  ] as const;

const pageThemes = {
  cyan: {
    panel: "border-cyan-300/20 bg-cyan-300/5",
    active:
      "border-cyan-300/60 bg-cyan-300/15 text-cyan-50 shadow-[0_0_28px_rgba(103,232,249,0.14)]",
    inactive:
      "border-white/10 bg-white/5 text-slate-300 hover:border-cyan-300/35 hover:bg-cyan-300/10 hover:text-white",
    eyebrow: "text-cyan-200/70",
    chip: "border-cyan-300/25 bg-cyan-300/10 text-cyan-100",
    sublabel: "text-cyan-200",
  },
  lime: {
    panel: "border-lime-300/20 bg-lime-300/5",
    active:
      "border-lime-300/60 bg-lime-300/15 text-lime-50 shadow-[0_0_28px_rgba(190,242,100,0.14)]",
    inactive:
      "border-white/10 bg-white/5 text-slate-300 hover:border-lime-300/35 hover:bg-lime-300/10 hover:text-white",
    eyebrow: "text-lime-200/70",
    chip: "border-lime-300/25 bg-lime-300/10 text-lime-100",
    sublabel: "text-lime-200",
  },
  violet: {
    panel: "border-violet-300/20 bg-violet-300/5",
    active:
      "border-violet-300/60 bg-violet-300/15 text-violet-50 shadow-[0_0_28px_rgba(196,181,253,0.14)]",
    inactive:
      "border-white/10 bg-white/5 text-slate-300 hover:border-violet-300/35 hover:bg-violet-300/10 hover:text-white",
    eyebrow: "text-violet-200/70",
    chip: "border-violet-300/25 bg-violet-300/10 text-violet-100",
    sublabel: "text-violet-200",
  },
  emerald: {
    panel: "border-emerald-300/20 bg-emerald-300/5",
    active:
      "border-emerald-300/60 bg-emerald-300/15 text-emerald-50 shadow-[0_0_28px_rgba(110,231,183,0.14)]",
    inactive:
      "border-white/10 bg-white/5 text-slate-300 hover:border-emerald-300/35 hover:bg-emerald-300/10 hover:text-white",
    eyebrow: "text-emerald-200/70",
    chip: "border-emerald-300/25 bg-emerald-300/10 text-emerald-100",
    sublabel: "text-emerald-200",
  },
  amber: {
    panel: "border-amber-300/20 bg-amber-300/5",
    active:
      "border-amber-300/60 bg-amber-300/15 text-amber-50 shadow-[0_0_28px_rgba(245,158,11,0.14)]",
    inactive:
      "border-white/10 bg-white/5 text-slate-300 hover:border-amber-300/35 hover:bg-amber-300/10 hover:text-white",
    eyebrow: "text-amber-200/70",
    chip: "border-amber-300/25 bg-amber-300/10 text-amber-100",
    sublabel: "text-amber-200",
  }
} as const;

function getActiveTheme(
  pathname: string,) {
  if (
    pathname.startsWith(
      "/doc-search",
    )
  ) {
    return pageThemes.lime;
  }

  if (
    pathname.startsWith(
      "/data",
    )
  ) {
    return pageThemes.amber;
  }

  if (
    pathname.startsWith(
      "/compare",
    )
  ) {
    return pageThemes.violet;
  }

  if (
    pathname.startsWith(
      "/history",
    )
  ) {
    return pageThemes.emerald;
  }

  return pageThemes.cyan;
}
export function Sidebar({ displayName, mode, onLogout }: SidebarProps) {
  const pathname = usePathname();
  const theme = getActiveTheme(pathname);

  const modeLabel =
    mode === "compare"
      ? "Compare Mode"
      : mode === "premium"
        ? "Premium"
        : "Basic";

  return (
    <aside className={`soft-panel border ${theme.panel} p-5 sm:p-6`}>
      <div className="flex flex-col gap-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className={`text-xs uppercase tracking-[0.32em] ${theme.eyebrow}`}>
              LLM Studio
            </p>

            <h2 className="mt-3 text-2xl font-semibold text-white">
              {displayName}
            </h2>

            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
              Secure finance inference workspace for provider-routed LLM
              workflows.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] ${theme.chip}`}
            >
              Finance AI
            </span>

            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-slate-300">
              {modeLabel}
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t border-white/10 pt-4 lg:flex-row lg:items-center lg:justify-between">
          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => {
              const isActive =
                item.href === "/dashboard"
                  ? pathname === "/dashboard"
                  : pathname.startsWith(item.href);

              const itemTheme = pageThemes[item.accent];

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={[
                    "group rounded-2xl border px-4 py-3 text-sm font-semibold transition",
                    isActive ? itemTheme.active : itemTheme.inactive,
                  ].join(" ")}
                >
                  <span className="block">{item.label}</span>
                  <span
                    className={[
                      "mt-0.5 block text-[10px] uppercase tracking-[0.18em]",
                      isActive
                        ? itemTheme.sublabel
                        : "text-slate-500 group-hover:text-slate-200",
                    ].join(" ")}
                  >
                    {item.description}
                  </span>
                </Link>
              );
            })}
          </nav>

          <button
            type="button"
            onClick={onLogout}
            className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm font-semibold text-slate-300 transition hover:border-rose-300/40 hover:bg-rose-400/10 hover:text-rose-100"
          >
            Sign out
          </button>
        </div>
      </div>
    </aside>
  );
}