import { mkdir, readFile, writeFile } from "fs/promises";
import path from "path";

import type { DocumentStorageProfile } from "./types";

export type OriginalFileStorage =
  | "none"
  | "local"
  | "supabase-storage"
  | "aws-s3";

export type VectorStorage =
  | "memory"
  | "local-json"
  | "local-sqlite"
  | "supabase-pgvector"
  | "aws-aurora"
  | "aws-opensearch";

export type MetadataStorage =
  | "memory"
  | "local-json"
  | "local-sqlite"
  | "supabase-postgres"
  | "aws-dynamodb"
  | "aws-aurora";

export type HistoryStorage =
  | "browser-local"
  | "local-json"
  | "supabase-postgres"
  | "aws";

export type RagStorageConfig = {
  profile: DocumentStorageProfile;
  originalFileStorage: OriginalFileStorage;
  vectorStorage: VectorStorage;
  metadataStorage: MetadataStorage;
  historyStorage: HistoryStorage;
  storeOriginalFiles: boolean;
  embeddingProvider: "openai";
  embeddingModel: string;
  chunkSizeChars: number;
  chunkOverlapChars: number;
  retrievalTopK: number;
  maxIndexedChars: number;
  updatedAt: string;
};

export function getEnabledProfiles(): DocumentStorageProfile[] {
  const profiles: DocumentStorageProfile[] = ["session", "local-json"];

  if (process.env.DOCUMENT_ENABLE_SUPABASE === "true") {
    profiles.push("supabase-pgvector");
  }

  return profiles;
}

export const disabledProfiles: Array<{
  profile: DocumentStorageProfile;
  label: string;
  reason: string;
}> = [
  {
    profile: "local-sqlite",
    label: "Local SQLite",
    reason: "Coming in a later 2B hardening pass.",
  },
  {
    profile: "supabase-pgvector",
    label: "Supabase pgvector",
    reason: "Cloud adapter belongs to Phase 2C.",
  },
  {
    profile: "aws",
    label: "AWS user-owned storage",
    reason: "AWS storage belongs to Phase 2C/2D and requires explicit cost controls.",
  },
  {
    profile: "export-import",
    label: "Export / import",
    reason: "Portable backups belong to Phase 2C/2D.",
  },
];

function numberFromEnv(name: string, fallback: number) {
  const value = process.env[name];

  if (!value) return fallback;

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function getStoreDir() {
  return path.join(
    process.cwd(),
    process.env.DOCUMENT_STORE_DIR ?? ".data/document-memory",
  );
}

function getConfigPath() {
  return path.join(getStoreDir(), "rag-config.json");
}

export function getDefaultRagConfig(): RagStorageConfig {
  const profile =
    process.env.DOCUMENT_MEMORY_PROFILE === "session"
      ? "session"
      : "local-json";

  return {
    profile,
    originalFileStorage: "none",
    vectorStorage: profile === "session" ? "memory" : "local-json",
    metadataStorage: profile === "session" ? "memory" : "local-json",
    historyStorage: "browser-local",
    storeOriginalFiles: false,
    embeddingProvider: "openai",
    embeddingModel:
      process.env.DOCUMENT_EMBEDDING_MODEL ?? "text-embedding-3-small",
    chunkSizeChars: numberFromEnv("DOCUMENT_CHUNK_SIZE_CHARS", 1800),
    chunkOverlapChars: numberFromEnv("DOCUMENT_CHUNK_OVERLAP_CHARS", 250),
    retrievalTopK: numberFromEnv("DOCUMENT_RETRIEVAL_TOP_K", 6),
    maxIndexedChars: numberFromEnv("DOCUMENT_MAX_INDEXED_CHARS", 300000),
    updatedAt: new Date().toISOString(),
  };
}

export async function readRagConfig(): Promise<RagStorageConfig> {
  try {
    const content = await readFile(getConfigPath(), "utf8");
    const parsed = JSON.parse(content) as Partial<RagStorageConfig>;
    const defaults = getDefaultRagConfig();

    return {
      ...defaults,
      ...parsed,
      storeOriginalFiles: false,
      originalFileStorage: "none",
      embeddingProvider: "openai",
    };
  } catch {
    return getDefaultRagConfig();
  }
}

export function buildConfigForProfile(
  profile: DocumentStorageProfile,
  currentConfig = getDefaultRagConfig(),
): RagStorageConfig {
  if (!getEnabledProfiles().includes(profile)) {
    throw new Error(`${profile} is not enabled in Phase 2B.`);
  }

  if (profile === "session") {
    return {
      ...currentConfig,
      profile: "session",
      originalFileStorage: "none",
      vectorStorage: "memory",
      metadataStorage: "memory",
      historyStorage: "browser-local",
      storeOriginalFiles: false,
      updatedAt: new Date().toISOString(),
    };
  }

  if (profile === "supabase-pgvector") {
  return {
    ...currentConfig,
    profile: "supabase-pgvector",
    originalFileStorage: "none",
    vectorStorage: "supabase-pgvector",
    metadataStorage: "supabase-postgres",
    historyStorage: "browser-local",
    storeOriginalFiles: false,
    updatedAt: new Date().toISOString(),
  };
}

  return {
    ...currentConfig,
    profile: "local-json",
    originalFileStorage: "none",
    vectorStorage: "local-json",
    metadataStorage: "local-json",
    historyStorage: "browser-local",
    storeOriginalFiles: false,
    updatedAt: new Date().toISOString(),
  };
}

export async function writeRagConfig(config: RagStorageConfig) {
  await mkdir(getStoreDir(), { recursive: true });
  await writeFile(getConfigPath(), JSON.stringify(config, null, 2), "utf8");
}