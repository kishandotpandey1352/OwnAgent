import type { HistoryEntry } from "@/types";

const HISTORY_STORAGE_KEY = "finance-llm-studio-history";

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

export function loadHistory(): HistoryEntry[] {
  if (!isBrowser()) {
    return [];
  }

  return safeJsonParse<HistoryEntry[]>(window.localStorage.getItem(HISTORY_STORAGE_KEY)) ?? [];
}

export function saveHistory(entries: HistoryEntry[]) {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(entries));
}

export function appendHistory(entry: HistoryEntry) {
  const nextEntries = [entry, ...loadHistory()].slice(0, 50);
  saveHistory(nextEntries);
  return nextEntries;
}

export function clearHistory() {
  if (!isBrowser()) {
    return;
  }

  window.localStorage.removeItem(HISTORY_STORAGE_KEY);
}
