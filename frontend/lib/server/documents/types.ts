export type DocumentStorageProfile =
  | "session"
  | "local-json"
  | "local-sqlite"
  | "supabase-pgvector"
  | "aws"
  | "export-import";

export type DocumentKind =
  | "pdf"
  | "docx"
  | "text"
  | "csv"
  | "image"
  | "unknown";

export type DocumentTask = "summarize" | "qa" | "risk-analysis";

export interface StoredDocument {
  id: string;
  userId: string;
  fileName: string;
  fileType: string;
  kind: DocumentKind;
  size: number;
  pageCount?: number;
  chunkCount: number;
  extractedChars: number;
  embeddingModel: string;
  storageProfile: DocumentStorageProfile;
  createdAt: string;
}

export interface StoredDocumentChunk {
  id: string;
  userId: string;
  documentId: string;
  fileName: string;
  chunkIndex: number;
  text: string;
  pageNumber?: number;
  tokenEstimate: number;
  charStart: number;
  charEnd: number;
  createdAt: string;
}

export interface StoredDocumentVector {
  id: string;
  userId: string;
  documentId: string;
  chunkId: string;
  embedding: number[];
  embeddingModel: string;
  createdAt: string;
}

export interface RetrievedSource {
  documentId: string;
  chunkId: string;
  fileName: string;
  chunkIndex: number;
  pageNumber?: number;
  score: number;
  snippet: string;
}

export interface VectorSearchInput {
  userId: string;
  documentIds?: string[];
  queryEmbedding: number[];
  topK: number;
}

export interface VectorSearchResult {
  chunk: StoredDocumentChunk;
  vector: StoredDocumentVector;
  score: number;
}