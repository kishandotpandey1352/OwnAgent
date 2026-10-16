import type {
  StoredDocument,
  StoredDocumentChunk,
  StoredDocumentVector,
  VectorSearchInput,
  VectorSearchResult,
} from "./types";

export interface VectorStoreAdapter {
  upsertDocument(document: StoredDocument): Promise<void>;
  upsertChunks(chunks: StoredDocumentChunk[]): Promise<void>;
  upsertVectors(vectors: StoredDocumentVector[]): Promise<void>;
  listDocuments(userId: string): Promise<StoredDocument[]>;
  getChunksByDocumentIds(
    userId: string,
    documentIds: string[],
  ): Promise<StoredDocumentChunk[]>;
  searchSimilar(input: VectorSearchInput): Promise<VectorSearchResult[]>;
  deleteDocument(userId: string, documentId: string): Promise<void>;
  clearUserMemory(userId: string): Promise<void>;
}

export function cosineSimilarity(left: number[], right: number[]) {
  if (!left.length || left.length !== right.length) {
    return 0;
  }

  let dot = 0;
  let leftMagnitude = 0;
  let rightMagnitude = 0;

  for (let index = 0; index < left.length; index += 1) {
    const leftValue = left[index] ?? 0;
    const rightValue = right[index] ?? 0;

    dot += leftValue * rightValue;
    leftMagnitude += leftValue * leftValue;
    rightMagnitude += rightValue * rightValue;
  }

  if (!leftMagnitude || !rightMagnitude) {
    return 0;
  }

  return dot / (Math.sqrt(leftMagnitude) * Math.sqrt(rightMagnitude));
}