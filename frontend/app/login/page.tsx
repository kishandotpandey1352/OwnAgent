"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { LoginForm } from "@/components/LoginForm";
import { loadAuth } from "@/lib/auth";
import type { AuthState } from "@/types";

export default function LoginPage() {
  const router = useRouter();
  const [auth, setAuth] = useState<AuthState | null>(null);

  useEffect(() => {
    const storedAuth = loadAuth();
    setAuth(storedAuth);

    if (storedAuth) {
      router.replace("/dashboard");
    }
  }, [router]);

  return (
    <main className="page-shell grid min-h-screen items-center gap-8 lg:grid-cols-[0.95fr_1.05fr]">
      <section className="space-y-6">
        <span className="inline-flex rounded-full border border-cyan-300/30 bg-cyan-300/10 px-3 py-1 text-xs uppercase tracking-[0.28em] text-cyan-100">
          Authentication
        </span>
        <h1 className="max-w-xl text-4xl font-semibold tracking-tight text-white sm:text-5xl">
          Sign in with a JWT, API key, or the current development token.
        </h1>
        <p className="max-w-xl text-base leading-8 text-slate-300">
          The backend currently expects `X-API-Key`, but the frontend stores a generic access token so the same UI can move to JWT-backed auth later without changing the form.
        </p>

        <div className="space-y-3 rounded-[28px] border border-white/10 bg-white/5 p-6 text-sm text-slate-300">
          <p className="text-xs uppercase tracking-[0.24em] text-slate-400">What is stored locally</p>
          <p>Display name, access token, and a remember-me preference.</p>
          <p>Tokens are sent as both `Authorization` and `X-API-Key` headers.</p>
          <p>History stays local until the backend grows a proper persistence API.</p>
        </div>

        <Link href="/" className="inline-flex rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-medium text-white transition hover:border-white/20 hover:bg-white/10">
          Back to overview
        </Link>
      </section>

      <section className="space-y-4">
        <LoginForm />
        {auth ? (
          <p className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">
            A saved session was found and the app is redirecting to the dashboard.
          </p>
        ) : null}
      </section>
    </main>
  );
}