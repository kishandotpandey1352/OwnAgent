"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ComparePanel } from "@/components/ComparePanel";
import { Sidebar } from "@/components/Sidebar";
import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import { getProviderById, providerCatalog } from "@/lib/models";
import type { AuthState, FinanceTask } from "@/types";
import { AppTopMenu } from "@/components/AppTopMenu";

function getTaskLabel(task: FinanceTask) {
  if (task === "summarize") return "Summarize";
  if (task === "qa") return "Q&A";
  return "Risk Analysis";
}

function getProviderTierLabel(providerId: string) {
  const provider = getProviderById(providerId);
  return provider.tier === "basic" ? "Basic" : "Premium";
}

function getProviderName(providerId: string) {
  return getProviderById(providerId).name;
}

export default function ComparePage() {
  const router = useRouter();

  const [auth, setAuth] = useState<AuthState | null>(null);
  const [task, setTask] = useState<FinanceTask>("risk-analysis");
  const [leftProviderId, setLeftProviderId] = useState("finance-adapter");
  const [rightProviderId, setRightProviderId] = useState("openai-4_1");

  useEffect(() => {
    const storedAuth = loadAuth();
    setAuth(storedAuth);
  }, []);

  function handleLogout() {
    clearAuth();
    setAuth(null);
    router.push("/login");
  }

  const leftProvider = getProviderById(leftProviderId);
  const rightProvider = getProviderById(rightProviderId);

  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar
          displayName={getDisplayName(auth)}
          mode="compare"
          onLogout={handleLogout}
        />

        <AppTopMenu />

        <div className="mx-auto w-full max-w-7xl space-y-4 px-3 pb-8">
          <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-xl shadow-black/20">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs uppercase tracking-[0.24em] text-violet-200/70">
                  Compare Models
                </p>

                <h1 className="mt-2 text-2xl font-semibold text-white">
                  Side-by-side finance model evaluation
                </h1>

                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Run the same finance prompt through two providers and compare
                  output quality, latency, routing behavior, and model metadata.
                </p>

                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full border border-violet-300/20 bg-violet-300/10 px-3 py-1 font-semibold text-violet-100">
                    Compare mode
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                    Task: {getTaskLabel(task)}
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                    {getProviderTierLabel(leftProviderId)} vs{" "}
                    {getProviderTierLabel(rightProviderId)}
                  </span>
                </div>
              </div>

              <div className="grid gap-2 text-sm lg:min-w-[320px]">
                <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-2">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                    Left provider
                  </p>
                  <p className="mt-1 truncate font-semibold text-slate-100">
                    {getProviderName(leftProviderId)}
                  </p>
                </div>

                <div className="rounded-2xl border border-white/10 bg-black/20 px-3 py-2">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">
                    Right provider
                  </p>
                  <p className="mt-1 truncate font-semibold text-slate-100">
                    {getProviderName(rightProviderId)}
                  </p>
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-3xl border border-white/10 bg-slate-950/75 p-4 shadow-xl shadow-black/15">
            <div className="mb-4 flex flex-col gap-3 border-b border-white/10 pb-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-violet-200/70">
                  Evaluation Workspace
                </p>
                <h2 className="mt-2 text-lg font-semibold text-white">
                  Run one prompt across two providers
                </h2>
                <p className="mt-1 text-sm leading-6 text-slate-400">
                  Choose providers, select a finance task, run the comparison,
                  and review both outputs side by side.
                </p>
              </div>

              <div className="flex flex-wrap gap-2 text-xs">
                <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 font-semibold text-cyan-100">
                  {leftProvider.name}
                </span>
                <span className="rounded-full border border-slate-700 bg-black/20 px-3 py-1 font-semibold text-slate-300">
                  vs
                </span>
                <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1 font-semibold text-emerald-100">
                  {rightProvider.name}
                </span>
              </div>
            </div>

            <ComparePanel
              auth={auth}
              task={task}
              providers={providerCatalog}
              leftProvider={leftProvider}
              rightProvider={rightProvider}
              onLeftProviderChange={setLeftProviderId}
              onRightProviderChange={setRightProviderId}
              onTaskChange={setTask}
            />
          </section>
        </div>
      </div>
    </main>
  );
}