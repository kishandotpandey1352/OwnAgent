import { NextResponse } from "next/server";

import {
  chunkDocumentText,
  normalizeDocumentText,
} from "@/lib/server/documents/chunk";
import {
  createEmbeddings,
  getEmbeddingModel,
} from "@/lib/server/documents/embeddings";
import { extractDocumentText } from "@/lib/server/documents/extract";
import { getConfiguredVectorStore } from "@/lib/server/documents/store-factory";
import type {
  StoredDocument,
  StoredDocumentVector,
} from "@/lib/server/documents/types";

import { writeRagAuditEvent } from "@/lib/server/documents/audit";
import { readRagConfig } from "@/lib/server/documents/config";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function numberFromEnv(name: string, fallback: number) {
  const value = process.env[name];

  if (!value) return fallback;

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

function looksLikeRawPdf(text: string) {
  const sample = text.slice(0, 4000);

  return (
    sample.includes("%PDF-") ||
    sample.includes("/FlateDecode") ||
    sample.includes("xref") ||
    sample.includes("endobj") ||
    sample.includes("endstream")
  );
}

export async function POST(request: Request) {
  const requestId = `rag-upload-${crypto.randomUUID()}`;
  const userId = getUserId(request);
  const maxIndexedChars = numberFromEnv("DOCUMENT_MAX_INDEXED_CHARS", 300000);
  const config = await readRagConfig();
  
  try {
    const formData = await request.formData();
    const fileValue = formData.get("file");

    if (!(fileValue instanceof File)) {
      return NextResponse.json(
        {
          ok: false,
          request_id: requestId,
          error: "No file was uploaded.",
        },
        { status: 400 },
      );
    }

    const file = fileValue;
    const extracted = await extractDocumentText(file);
    const normalizedText = normalizeDocumentText(extracted.text);

    console.info(
      JSON.stringify({
        event: "rag_extraction_debug",
        requestId,
        userId,
        fileName: file.name,
        fileType: file.type,
        detectedKind: extracted.kind,
        pageCount: extracted.pageCount,
        extractedChars: normalizedText.length,
        extractedPreview: normalizedText.slice(0, 300),
        timestamp: new Date().toISOString(),
      }),
    );

    if (!normalizedText) {
      return NextResponse.json(
        {
          ok: false,
          request_id: requestId,
          error: "No text could be extracted from this document.",
        },
        { status: 400 },
      );
    }

    if (looksLikeRawPdf(normalizedText)) {
      return NextResponse.json(
        {
          ok: false,
          request_id: requestId,
          error:
            "PDF extraction failed. The document was read as raw PDF data instead of readable text, so it was not indexed.",
        },
        { status: 400 },
      );
    }

    const indexableText =
      normalizedText.length > maxIndexedChars
        ? `${normalizedText.slice(
            0,
            maxIndexedChars,
          )}\n\n[Document truncated at ${maxIndexedChars} characters for indexing.]`
        : normalizedText;

    const documentId = `doc-${crypto.randomUUID()}`;

    const chunks = chunkDocumentText({
      userId,
      documentId,
      fileName: file.name,
      text: indexableText,
    });

    if (!chunks.length) {
      return NextResponse.json(
        {
          ok: false,
          request_id: requestId,
          error: "Document text could not be split into chunks.",
        },
        { status: 400 },
      );
    }

    const embeddingResult = await createEmbeddings(
      chunks.map((chunk) => chunk.text),
    );

    const vectors: StoredDocumentVector[] = embeddingResult.embeddings.map(
      (embedding, index) => ({
        id: `vec-${crypto.randomUUID()}`,
        userId,
        documentId,
        chunkId: chunks[index].id,
        embedding,
        embeddingModel: embeddingResult.model,
        createdAt: new Date().toISOString(),
      }),
    );

    const document: StoredDocument = {
      id: documentId,
      userId,
      fileName: file.name,
      fileType: file.type,
      kind: extracted.kind,
      size: file.size,
      pageCount: extracted.pageCount,
      chunkCount: chunks.length,
      extractedChars: indexableText.length,
      embeddingModel: getEmbeddingModel(),
      storageProfile: "local-json",
      createdAt: new Date().toISOString(),
    };

    const store = await getVectorStore();

    await store.upsertDocument(document);
    await store.upsertChunks(chunks);
    await store.upsertVectors(vectors);

    console.info(
      JSON.stringify({
        event: "rag_document_indexed",
        requestId,
        userId,
        documentId,
        fileName: file.name,
        fileType: file.type,
        kind: extracted.kind,
        pageCount: extracted.pageCount,
        chunkCount: chunks.length,
        vectorCount: vectors.length,
        extractedChars: indexableText.length,
        embeddingModel: embeddingResult.model,
        timestamp: new Date().toISOString(),
      }),
    );

    await writeRagAuditEvent({
  userId,
  eventType: "document_indexed",
  documentId: document.id,
  fileName: document.fileName,
  embeddingModel: document.embeddingModel,
  metadata: {
    chunkCount: chunks.length,
    extractedChars: document.extractedChars,
    fileType: document.fileType,
    storageProfile: config.profile,
  },
});

    return NextResponse.json({
      ok: true,
      request_id: requestId,
      document,
      chunksIndexed: chunks.length,
      vectorsIndexed: vectors.length,
      usage: embeddingResult.usage,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Document indexing failed.";

    console.error(
      JSON.stringify({
        event: "rag_document_index_failed",
        requestId,
        userId,
        error: message,
        timestamp: new Date().toISOString(),
      }),
    );

    return NextResponse.json(
      {
        ok: false,
        request_id: requestId,
        error: message,
      },
      { status: 500 },
    );
  }
}

function getVectorStore() {
  return getConfiguredVectorStore();
}
