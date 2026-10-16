import type {
  StoredDocument,
  StoredDocumentChunk,
  StoredDocumentVector,
  VectorSearchInput,
  VectorSearchResult,
} from "../types";
import type { VectorStoreAdapter } from "../vector-store";
import { getSupabaseServerClient } from "./supabase-client";

type MatchRow = {
  chunk_id: string;
  document_id: string;
  file_name: string;
  chunk_index: number;
  page_number: number | null;
  text: string;
  score: number;
};

function toVectorLiteral(embedding: number[]) {
  return `[${embedding.join(",")}]`;
}

export class SupabasePgvectorStore implements VectorStoreAdapter {
  async upsertDocument(document: StoredDocument) {
    const supabase = getSupabaseServerClient();

    const { error } = await supabase.from("rag_documents").upsert({
      id: document.id,
      user_id: document.userId,
      file_name: document.fileName,
      file_type: document.fileType,
      kind: document.kind,
      size: document.size,
      page_count: document.pageCount ?? null,
      chunk_count: document.chunkCount,
      extracted_chars: document.extractedChars,
      embedding_model: document.embeddingModel,
      storage_profile: document.storageProfile,
      created_at: document.createdAt,
    });

    if (error) {
      throw new Error(error.message);
    }
  }

  async upsertChunks(chunks: StoredDocumentChunk[]) {
    if (!chunks.length) return;

    const supabase = getSupabaseServerClient();

    const { error } = await supabase.from("rag_chunks").upsert(
      chunks.map((chunk) => ({
        id: chunk.id,
        user_id: chunk.userId,
        document_id: chunk.documentId,
        file_name: chunk.fileName,
        chunk_index: chunk.chunkIndex,
        text: chunk.text,
        page_number: chunk.pageNumber ?? null,
        token_estimate: chunk.tokenEstimate,
        char_start: chunk.charStart,
        char_end: chunk.charEnd,
        created_at: chunk.createdAt,
      })),
    );

    if (error) {
      throw new Error(error.message);
    }
  }

  async upsertVectors(vectors: StoredDocumentVector[]) {
    if (!vectors.length) return;

    const supabase = getSupabaseServerClient();

    const { error } = await supabase.from("rag_vectors").upsert(
      vectors.map((vector) => ({
        id: vector.id,
        user_id: vector.userId,
        document_id: vector.documentId,
        chunk_id: vector.chunkId,
        embedding: toVectorLiteral(vector.embedding),
        embedding_model: vector.embeddingModel,
        created_at: vector.createdAt,
      })),
    );

    if (error) {
      throw new Error(error.message);
    }
  }

  async listDocuments(userId: string) {
    const supabase = getSupabaseServerClient();

    const { data, error } = await supabase
      .from("rag_documents")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });

    if (error) {
      throw new Error(error.message);
    }

    return (data ?? []).map((item) => ({
      id: item.id,
      userId: item.user_id,
      fileName: item.file_name,
      fileType: item.file_type,
      kind: item.kind,
      size: item.size,
      pageCount: item.page_count ?? undefined,
      chunkCount: item.chunk_count,
      extractedChars: item.extracted_chars,
      embeddingModel: item.embedding_model,
      storageProfile: item.storage_profile,
      createdAt: item.created_at,
    })) as StoredDocument[];
  }

  async getChunksByDocumentIds(userId: string, documentIds: string[]) {
    const supabase = getSupabaseServerClient();

    const { data, error } = await supabase
      .from("rag_chunks")
      .select("*")
      .eq("user_id", userId)
      .in("document_id", documentIds);

    if (error) {
      throw new Error(error.message);
    }

    return (data ?? []).map((item) => ({
      id: item.id,
      userId: item.user_id,
      documentId: item.document_id,
      fileName: item.file_name,
      chunkIndex: item.chunk_index,
      text: item.text,
      pageNumber: item.page_number ?? undefined,
      tokenEstimate: item.token_estimate,
      charStart: item.char_start,
      charEnd: item.char_end,
      createdAt: item.created_at,
    })) as StoredDocumentChunk[];
  }

  async searchSimilar(input: VectorSearchInput): Promise<VectorSearchResult[]> {
    const supabase = getSupabaseServerClient();

    const { data, error } = await supabase.rpc("match_rag_chunks", {
      query_embedding: toVectorLiteral(input.queryEmbedding),
      match_user_id: input.userId,
      match_document_ids: input.documentIds ?? [],
      match_count: input.topK,
    });

    if (error) {
      throw new Error(error.message);
    }

    return ((data ?? []) as MatchRow[]).map((row) => ({
      chunk: {
        id: row.chunk_id,
        userId: input.userId,
        documentId: row.document_id,
        fileName: row.file_name,
        chunkIndex: row.chunk_index,
        text: row.text,
        pageNumber: row.page_number ?? undefined,
        tokenEstimate: Math.ceil(row.text.length / 4),
        charStart: 0,
        charEnd: row.text.length,
        createdAt: new Date().toISOString(),
      },
      vector: {
        id: `remote-${row.chunk_id}`,
        userId: input.userId,
        documentId: row.document_id,
        chunkId: row.chunk_id,
        embedding: [],
        embeddingModel: process.env.DOCUMENT_EMBEDDING_MODEL ?? "text-embedding-3-small",
        createdAt: new Date().toISOString(),
      },
      score: row.score,
    }));
  }

  async deleteDocument(userId: string, documentId: string) {
  const supabase = getSupabaseServerClient();

  const { error } = await supabase
    .from("rag_documents")
    .delete()
    .eq("user_id", userId)
    .eq("id", documentId);

  if (error) {
    throw new Error(`Failed to delete Supabase document: ${error.message}`);
  }
}

async clearUserMemory(userId: string) {
  const supabase = getSupabaseServerClient();

  const { error } = await supabase
    .from("rag_documents")
    .delete()
    .eq("user_id", userId);

  if (error) {
    throw new Error(`Failed to clear Supabase document memory: ${error.message}`);
  }
}
}