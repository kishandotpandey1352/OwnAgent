import type { AuthState } from "@/types";

const AUTH_STORAGE_KEY = "finance-llm-studio-auth";

function isBrowser() {
  return typeof window !== "undefined";
}

function safeJsonParse<T>(value: string | null): T | null {
  if (!value) {
    return null;
  }

  try {
    return JSON.parse(value) as T;
  } catch {
    return null;
  }
}

export function createAuthState(displayName: string, accessToken: string, remember: boolean): AuthState {
  return {
    displayName,
    accessToken,
    remember,
    issuedAt: new Date().toISOString(),
  };
}

export function loadAuth(): AuthState | null {
  if (!isBrowser()) {
    return null;
  }

  return safeJsonParse<AuthState>(window.localStorage.getItem(AUTH_STORAGE_KEY));
}

export function saveAuth(authState: AuthState) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authState));
}

export function clearAuth() {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

export function getDisplayName(authState: AuthState | null) {
  return authState?.displayName?.trim() || "Demo operator";
}

export function getAuthHeaderValue(authState: AuthState | null) {
  return authState?.accessToken?.trim() || "";
}
