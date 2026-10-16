"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { clearAuth, getDisplayName, loadAuth } from "@/lib/auth";
import type { AuthState } from "@/types";
import { MemoryPreferencesDialog } from "./MemoryPreferencesDialog";

export function AppTopMenu() {
  const router = useRouter();
  const menuRef = useRef<HTMLDivElement | null>(null);

  const [auth, setAuth] = useState<AuthState | null>(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);

  useEffect(() => {
    setAuth(loadAuth());
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        event.target instanceof Node &&
        !menuRef.current.contains(event.target)
      ) {
        setIsMenuOpen(false);
      }
    }

    if (isMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isMenuOpen]);

  function handleLogout() {
    clearAuth();
    setAuth(null);
    setIsMenuOpen(false);
    router.push("/login");
  }

  function openMemoryDialog() {
    setIsMenuOpen(false);
    setIsMemoryOpen(true);
  }

  const displayName = getDisplayName(auth);

  return (
    <>
      <div ref={menuRef} className="fixed right-4 top-4 z-50">
        <button
          type="button"
          onClick={() => setIsMenuOpen((current) => !current)}
          className="flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-950/90 px-3 py-2 text-left shadow-xl shadow-black/30 backdrop-blur transition hover:border-cyan-300/30 hover:bg-slate-900"
          aria-label="Open settings menu"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-300 text-sm font-bold text-slate-950">
            {displayName?.slice(0, 1).toUpperCase() ?? "U"}
          </span>

          <span className="hidden min-w-0 sm:block">
            <span className="block max-w-[150px] truncate text-xs font-semibold text-white">
              {displayName}
            </span>
            <span className="block text-[11px] text-slate-400">
              Settings
            </span>
          </span>

          <span className="text-slate-400">⌄</span>
        </button>

        {isMenuOpen ? (
          <div className="absolute right-0 mt-2 w-72 overflow-hidden rounded-2xl border border-white/10 bg-slate-950/95 shadow-2xl shadow-black/40 backdrop-blur">
            <div className="border-b border-white/10 px-4 py-3">
              <p className="text-sm font-semibold text-white">{displayName}</p>
              <p className="mt-1 text-xs text-slate-400">
                Finance AI Platform
              </p>
            </div>

            <div className="p-2">
              <button
                type="button"
                onClick={openMemoryDialog}
                className="w-full rounded-xl px-3 py-2.5 text-left transition hover:bg-white/5"
              >
                <span className="block text-sm font-semibold text-white">
                  Memory preferences
                </span>
                <span className="mt-0.5 block text-xs leading-5 text-slate-400">
                  View, confirm, add, or delete saved preferences.
                </span>
              </button>

              <button
                type="button"
                disabled
                className="w-full cursor-not-allowed rounded-xl px-3 py-2.5 text-left opacity-50"
              >
                <span className="block text-sm font-semibold text-white">
                  Provider settings
                </span>
                <span className="mt-0.5 block text-xs leading-5 text-slate-400">
                  Coming later for model routing preferences.
                </span>
              </button>

              <button
                type="button"
                disabled
                className="w-full cursor-not-allowed rounded-xl px-3 py-2.5 text-left opacity-50"
              >
                <span className="block text-sm font-semibold text-white">
                  Storage settings
                </span>
                <span className="mt-0.5 block text-xs leading-5 text-slate-400">
                  Use Doc Search configuration for now.
                </span>
              </button>
            </div>

            <div className="border-t border-white/10 p-2">
              <button
                type="button"
                onClick={handleLogout}
                className="w-full rounded-xl px-3 py-2.5 text-left text-sm font-semibold text-rose-100 transition hover:bg-rose-400/10"
              >
                Logout
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <MemoryPreferencesDialog
        open={isMemoryOpen}
        onClose={() => setIsMemoryOpen(false)}
      />
    </>
  );
}