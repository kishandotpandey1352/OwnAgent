"use client";

import {
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { AppTopMenu } from "@/components/AppTopMenu";
import { DataWorkspace } from "@/components/DataWorkspace";
import { Sidebar } from "@/components/Sidebar";

import {
  clearAuth,
  getDisplayName,
  loadAuth,
} from "@/lib/auth";

import type {
  AuthState,
} from "@/types";


export default function DataPage() {
  const router = useRouter();

  const [
    auth,
    setAuth,
  ] =
    useState<AuthState | null>(
      null,
    );


  useEffect(() => {
    setAuth(
      loadAuth(),
    );
  }, []);


  function handleLogout() {
    clearAuth();

    setAuth(null);

    router.push(
      "/login",
    );
  }


  return (
    <main className="page-shell">
      <div className="app-grid">
        <Sidebar
          displayName={getDisplayName(
            auth,
          )}
          mode="premium"
          onLogout={
            handleLogout
          }
        />

        <AppTopMenu />

        <div className="mx-auto w-full max-w-7xl space-y-4 px-3 pb-8">
          <section className="rounded-3xl border border-white/10 bg-slate-950/80 p-5 shadow-xl shadow-black/20">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div className="max-w-3xl">
                <p className="text-xs uppercase tracking-[0.24em] text-amber-200/70">
                  Data Analysis
                </p>

                <h1 className="mt-2 text-2xl font-semibold text-white">
                  Analyze financial CSV data
                </h1>

                <p className="mt-2 text-sm leading-6 text-slate-300">
                  Upload structured finance data, inspect column
                  types and missing values, review deterministic
                  statistics, and send the profile to the finance
                  agent for analysis.
                </p>

                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 font-semibold text-amber-100">
                    pandas analysis
                  </span>

                  <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 font-semibold text-cyan-100">
                    LangGraph tools
                  </span>

                  <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-300">
                    No RAG
                  </span>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Phase
                </p>

                <p className="mt-1 text-sm font-semibold text-white">
                  3E · CSV Analysis MVP
                </p>

                <p className="mt-1 text-xs text-slate-400">
                  Chart rendering arrives in 3F.
                </p>
              </div>
            </div>
          </section>

          <DataWorkspace />
        </div>
      </div>
    </main>
  );
}