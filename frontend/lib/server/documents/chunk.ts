import type { StoredDocumentChunk } from "./types";

function numberFromEnv(name: string, fallback: number) {
  const value = process.env[name];

  if (!value) return fallback;

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function estimateTokens(text: string) {
  return Math.ceil(text.length / 4);
}

export function normalizeDocumentText(text: string) {
  return text
    .replace(/\u0000/g, "")
    .replace(/\r\n/g, "\n")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{4,}/g, "\n\n\n")
    .trim();
}

export function chunkDocumentText(input: {
  userId: string;
  documentId: string;
  fileName: string;
  text: string;
}) {
  const chunkSize = numberFromEnv("DOCUMENT_CHUNK_SIZE_CHARS", 1800);
  const overlap = numberFromEnv("DOCUMENT_CHUNK_OVERLAP_CHARS", 250);
  const normalized = normalizeDocumentText(input.text);
  const chunks: StoredDocumentChunk[] = [];

  if (!normalized) {
    return chunks;
  }

  let start = 0;
  let chunkIndex = 0;

  while (start < normalized.length) {
    const hardEnd = Math.min(start + chunkSize, normalized.length);
    let end = hardEnd;

    const paragraphBreak = normalized.lastIndexOf("\n\n", hardEnd);
    if (paragraphBreak > start + Math.floor(chunkSize * 0.5)) {
      end = paragraphBreak;
    }

    const text = normalized.slice(start, end).trim();

    if (text) {
      chunks.push({
        id: `chunk-${crypto.randomUUID()}`,
        userId: input.userId,
        documentId: input.documentId,
        fileName: input.fileName,
        chunkIndex,
        text,
        tokenEstimate: estimateTokens(text),
        charStart: start,
        charEnd: end,
        createdAt: new Date().toISOString(),
      });

      chunkIndex += 1;
    }

    if (end >= normalized.length) break;

    start = Math.max(0, end - overlap);
  }

  return chunks;
}