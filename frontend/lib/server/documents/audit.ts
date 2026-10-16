import { getConfiguredVectorStore } from "./store-factory";
import { readRagConfig } from "./config";
import { getSupabaseServerClient } from "./stores/supabase-client";

type RagAuditEventInput = {
  userId: string;
  eventType:
    | "document_uploaded"
    | "document_indexed"
    | "document_queried"
    | "document_deleted"
    | "memory_cleared"
    | "low_similarity_warning"
    | "supabase_delete_cascade_completed"
    | "unsupported_claim_detected"
    | "low_confidence_answer";
  documentId?: string;
  fileName?: string;
  embeddingModel?: string;
  metadata?: Record<string, unknown>;
};

export async function writeRagAuditEvent(input: RagAuditEventInput) {
  const config = await readRagConfig();

  if (config.profile !== "supabase-pgvector") {
    console.info(
      JSON.stringify({
        event: "rag_audit_event",
        userId: input.userId,
        eventType: input.eventType,
        documentId: input.documentId,
        fileName: input.fileName,
        storageProfile: config.profile,
        embeddingModel: input.embeddingModel ?? config.embeddingModel,
        metadata: input.metadata ?? {},
        timestamp: new Date().toISOString(),
      }),
    );

    return;
  }

  const supabase = getSupabaseServerClient();

  const { error } = await supabase.from("rag_audit_events").insert({
    id: crypto.randomUUID(),
    user_id: input.userId,
    event_type: input.eventType,
    document_id: input.documentId ?? null,
    file_name: input.fileName ?? null,
    storage_profile: config.profile,
    embedding_model: input.embeddingModel ?? config.embeddingModel,
    metadata: input.metadata ?? {},
    created_at: new Date().toISOString(),
  });

  if (error) {
    console.warn(
      JSON.stringify({
        event: "rag_audit_write_failed",
        userId: input.userId,
        eventType: input.eventType,
        error: error.message,
        timestamp: new Date().toISOString(),
      }),
    );
  }
}