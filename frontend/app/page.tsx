import Link from "next/link";

import { providerCatalog, tasks } from "@/lib/models";

export default function HomePage() {
  return (
    <main className="page-shell space-y-8">
      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="soft-panel relative overflow-hidden p-8 sm:p-10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(34,211,238,0.18),transparent_30%),radial-gradient(circle_at_bottom_left,rgba(59,130,246,0.12),transparent_28%)]" />
          <div className="relative space-y-6">
            <span className="inline-flex rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs uppercase tracking-[0.28em] text-cyan-100">
              LLM Studio
            </span>
            <div className="space-y-4">
              <h1 className="max-w-3xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
                A focused frontend for financial inference, provider comparison, and traceable usage metadata.
              </h1>
              <p className="max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
                This workspace is wired for the secure FastAPI gateway, JWT or API-key sign-in, live or mock inference, and side-by-side premium model comparisons.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link href="/login" className="rounded-2xl bg-gradient-to-r from-cyan-400 to-sky-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110">
                Open login
              </Link>
              <Link href="/dashboard" className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10">
                Open dashboard
              </Link>
            </div>
          </div>
        </div>

        <div className="grid gap-4">
          <div className="frost-card p-6">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Ready routes</p>
            <ul className="mt-4 space-y-3 text-sm text-slate-200">
              <li>Login and token storage</li>
              <li>Basic and Premium dashboard flow</li>
              <li>Comparison workspace</li>
              <li>Local history persistence</li>
            </ul>
          </div>
          <div className="frost-card p-6">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Tasks</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              {tasks.map((task) => (
                <div key={task.value} className="rounded-2xl border border-white/10 bg-black/15 p-4">
                  <p className="font-semibold text-white">{task.label}</p>
                  <p className="mt-2 text-xs leading-6 text-slate-400">{task.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        {providerCatalog.map((provider) => (
          <article key={provider.id} className="frost-card p-6">
            <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{provider.provider}</p>
            <h2 className="mt-2 text-xl font-semibold text-white">{provider.name}</h2>
            <p className="mt-3 text-sm leading-7 text-slate-300">{provider.description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}