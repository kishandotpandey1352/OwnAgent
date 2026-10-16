import { readRagConfig } from "./config";
import type { VectorStoreAdapter } from "./vector-store";
import { LocalJsonVectorStore } from "./stores/local-json";
import { SupabasePgvectorStore } from "./stores/supabase-pgvector";

export async function getConfiguredVectorStore(): Promise<VectorStoreAdapter> {
  const config = await readRagConfig();

  if (config.profile === "supabase-pgvector") {
    if (process.env.DOCUMENT_ENABLE_SUPABASE !== "true") {
      throw new Error(
        "Supabase document memory is configured but DOCUMENT_ENABLE_SUPABASE is not true.",
      );
    }

    return new SupabasePgvectorStore();
  }

  return new LocalJsonVectorStore();
}