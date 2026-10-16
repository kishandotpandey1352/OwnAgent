"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { createAuthState, saveAuth } from "@/lib/auth";
import type { AuthState } from "@/types";

interface LoginFormProps {
  onSuccess?: (authState: AuthState) => void;
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("Finance operator");
  const [accessToken, setAccessToken] = useState("dev-finance-api-key");
  const [remember, setRemember] = useState(true);
  const [status, setStatus] = useState<"idle" | "saving">("idle");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!displayName.trim() || !accessToken.trim()) {
      setError("Enter both a display name and a token or API key.");
      return;
    }

    setStatus("saving");

    const authState = createAuthState(displayName.trim(), accessToken.trim(), remember);
    saveAuth(authState);
    onSuccess?.(authState);

    router.push("/dashboard");
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5 rounded-[32px] border border-white/10 bg-panel/90 p-6 shadow-halo backdrop-blur-xl">
      <div>
        <p className="text-xs uppercase tracking-[0.28em] text-cyan-200/70">Secure sign-in</p>
        <h2 className="mt-2 text-3xl font-semibold text-white">Connect your gateway token</h2>
        <p className="mt-2 text-sm text-slate-400">Use a JWT from the future FastAPI gateway or the current dev API key. The frontend sends both headers for compatibility.</p>
      </div>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-slate-200">Display name</span>
        <input
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          className="w-full rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20"
          placeholder="Finance operator"
        />
      </label>

      <label className="block space-y-2">
        <span className="text-sm font-medium text-slate-200">API key or JWT</span>
        <input
          value={accessToken}
          onChange={(event) => setAccessToken(event.target.value)}
          className="w-full rounded-2xl border border-white/10 bg-black/25 px-4 py-3 font-mono text-sm text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50 focus:ring-2 focus:ring-cyan-400/20"
          placeholder="dev-finance-api-key"
        />
      </label>

      <label className="flex items-center gap-3 text-sm text-slate-300">
        <input
          checked={remember}
          onChange={(event) => setRemember(event.target.checked)}
          type="checkbox"
          className="h-4 w-4 rounded border-white/20 bg-black/20 text-cyan-400 focus:ring-cyan-400"
        />
        Remember this token on the device
      </label>

      {error ? <p className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</p> : null}

      <button
        type="submit"
        disabled={status === "saving"}
        className="w-full rounded-2xl bg-gradient-to-r from-cyan-400 to-sky-500 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {status === "saving" ? "Saving session..." : "Open dashboard"}
      </button>
    </form>
  );
}