import { mkdir, readFile, writeFile } from "fs/promises";
import path from "path";

import type {
  StoredDocument,
  StoredDocumentChunk,
  StoredDocumentVector,
  VectorSearchInput,
  VectorSearchResult,
} from "../types";
import { cosineSimilarity, type VectorStoreAdapter } from "../vector-store";

type LocalStoreData = {
  documents: StoredDocument[];
  chunks: StoredDocumentChunk[];
  vectors: StoredDocumentVector[];
};

function getStoreDir() {
  return path.join(process.cwd(), process.env.DOCUMENT_STORE_DIR ?? ".data/document-memory");
}

function getStoreFilePath() {
  return path.join(getStoreDir(), "rag-store.json");
}

async function readStore(): Promise<LocalStoreData> {
  const filePath = getStoreFilePath();

  try {
    const content = await readFile(filePath, "utf8");
    return JSON.parse(content) as LocalStoreData;
  } catch {
    return {
      documents: [],
      chunks: [],
      vectors: [],
    };
  }
}

async function writeStore(data: LocalStoreData) {
  await mkdir(getStoreDir(), { recursive: true });
  await writeFile(getStoreFilePath(), JSON.stringify(data, null, 2), "utf8");
}

export class LocalJsonVectorStore implements VectorStoreAdapter {
  async upsertDocument(document: StoredDocument) {
    const data = await readStore();

    data.documents = [
      ...data.documents.filter((item) => item.id !== document.id),
      document,
    ];

    await writeStore(data);
  }

  async upsertChunks(chunks: StoredDocumentChunk[]) {
    const data = await readStore();
    const incomingIds = new Set(chunks.map((chunk) => chunk.id));

    data.chunks = [
      ...data.chunks.filter((chunk) => !incomingIds.has(chunk.id)),
      ...chunks,
    ];

    await writeStore(data);
  }

  async upsertVectors(vectors: StoredDocumentVector[]) {
    const data = await readStore();
    const incomingIds = new Set(vectors.map((vector) => vector.id));

    data.vectors = [
      ...data.vectors.filter((vector) => !incomingIds.has(vector.id)),
      ...vectors,
    ];

    await writeStore(data);
  }

  async listDocuments(userId: string) {
    const data = await readStore();

    return data.documents
      .filter((document) => document.userId === userId)
      .sort((left, right) => right.createdAt.localeCompare(left.createdAt));
  }

  async getChunksByDocumentIds(userId: string, documentIds: string[]) {
    const data = await readStore();
    const allowedDocumentIds = new Set(documentIds);

    return data.chunks.filter(
      (chunk) =>
        chunk.userId === userId && allowedDocumentIds.has(chunk.documentId),
    );
  }

  async searchSimilar(input: VectorSearchInput): Promise<VectorSearchResult[]> {
    const data = await readStore();
    const allowedDocumentIds = input.documentIds?.length
      ? new Set(input.documentIds)
      : undefined;

    const chunkById = new Map(
      data.chunks
        .filter((chunk) => chunk.userId === input.userId)
        .map((chunk) => [chunk.id, chunk]),
    );

    return data.vectors
      .filter((vector) => {
        if (vector.userId !== input.userId) return false;
        if (allowedDocumentIds && !allowedDocumentIds.has(vector.documentId)) {
          return false;
        }

        return true;
      })
      .map((vector) => {
        const chunk = chunkById.get(vector.chunkId);

        if (!chunk) return null;

        return {
          chunk,
          vector,
          score: cosineSimilarity(input.queryEmbedding, vector.embedding),
        };
      })
      .filter((item): item is VectorSearchResult => Boolean(item))
      .sort((left, right) => right.score - left.score)
      .slice(0, input.topK);
  }

  async deleteDocument(userId: string, documentId: string) {
    const data = await readStore();

    data.documents = data.documents.filter(
      (document) => !(document.userId === userId && document.id === documentId),
    );

    data.chunks = data.chunks.filter(
      (chunk) => !(chunk.userId === userId && chunk.documentId === documentId),
    );

    data.vectors = data.vectors.filter(
      (vector) => !(vector.userId === userId && vector.documentId === documentId),
    );

    await writeStore(data);
  }


  async clearUserMemory(userId: string) {
  const data = await readStore();

    data.documents = data.documents.filter(
      (document) => document.userId !== userId,
    );

    data.chunks = data.chunks.filter((chunk) => chunk.userId !== userId);

    data.vectors = data.vectors.filter((vector) => vector.userId !== userId);

    await writeStore(data);
  }

}

export function getVectorStore() {
  return new LocalJsonVectorStore();
}