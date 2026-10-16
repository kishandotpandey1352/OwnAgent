import mammoth from "mammoth";

import type { DocumentKind } from "./types";

type PdfParseResult = {
  text?: string;
  numpages?: number;
};

type PdfParseModule = {
  default?: PdfParseFunction;
};

type PdfParseFunction = (buffer: Buffer) => Promise<PdfParseResult>;

export type ExtractedDocumentText = {
  kind: DocumentKind;
  text: string;
  pageCount?: number;
};

export function getDocumentKind(file: File): DocumentKind {
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();

  if (type === "application/pdf" || name.endsWith(".pdf")) {
    return "pdf";
  }

  if (
    type ===
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ||
    name.endsWith(".docx")
  ) {
    return "docx";
  }

  if (
    type === "text/plain" ||
    type === "text/markdown" ||
    name.endsWith(".txt") ||
    name.endsWith(".md")
  ) {
    return "text";
  }

  if (
    type === "text/csv" ||
    type === "application/csv" ||
    name.endsWith(".csv")
  ) {
    return "csv";
  }

  if (
    type === "image/png" ||
    type === "image/jpeg" ||
    type === "image/webp" ||
    name.endsWith(".png") ||
    name.endsWith(".jpg") ||
    name.endsWith(".jpeg") ||
    name.endsWith(".webp")
  ) {
    return "image";
  }

  return "unknown";
}

export function isSupportedIndexFile(file: File) {
  const kind = getDocumentKind(file);

  return kind === "pdf" || kind === "docx" || kind === "text" || kind === "csv";
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

function meaningfulTextScore(text: string) {
  if (!text.trim()) return 0;

  const sample = text.slice(0, 8000);
  const letters = sample.match(/[A-Za-z]/g)?.length ?? 0;
  const numbers = sample.match(/[0-9]/g)?.length ?? 0;
  const whitespace = sample.match(/\s/g)?.length ?? 0;
  const replacementChars = sample.match(/\uFFFD/g)?.length ?? 0;
  const controlChars = sample.match(/[\x00-\x08\x0E-\x1F]/g)?.length ?? 0;

  return letters + numbers * 0.4 + whitespace * 0.05 - replacementChars * 5 - controlChars * 10;
}

function assertReadableExtraction(text: string, fileName: string) {
  const trimmed = text.trim();

  if (!trimmed) {
    throw new Error(
      `No readable text could be extracted from ${fileName}. This may be a scanned PDF, image-only document, or unsupported PDF encoding.`,
    );
  }

  if (looksLikeRawPdf(trimmed)) {
    throw new Error(
      `${fileName} was read as raw PDF data instead of extracted text. PDF extraction failed, so the document was not indexed.`,
    );
  }

  if (meaningfulTextScore(trimmed) < 80) {
    throw new Error(
      `${fileName} did not produce enough readable text to index safely. Try exporting the file as text, DOCX, CSV, TXT, or a text-based PDF.`,
    );
  }
}

async function extractPdfText(buffer: Buffer, fileName: string) {
  const pdfParseModule = (await import(
    "pdf-parse/lib/pdf-parse.js"
  )) as PdfParseModule | PdfParseFunction;

  const pdfParse =
    typeof pdfParseModule === "function"
      ? pdfParseModule
      : pdfParseModule.default;

  if (!pdfParse) {
    throw new Error("PDF parser could not be loaded.");
  }

  const result = await pdfParse(buffer);
  const text = result.text ?? "";

  assertReadableExtraction(text, fileName);

  return {
    text,
    pageCount: result.numpages ?? undefined,
  };
}

async function extractDocxText(buffer: Buffer, fileName: string) {
  const result = await mammoth.extractRawText({ buffer });
  const text = result.value ?? "";

  assertReadableExtraction(text, fileName);

  return {
    text,
    pageCount: undefined,
  };
}

function buildCsvText(text: string, fileName: string) {
  const lines = text.split(/\r?\n/).filter(Boolean);
  const previewLines = lines.slice(0, 1000);

  if (!previewLines.length) {
    throw new Error(`No readable CSV rows could be extracted from ${fileName}.`);
  }

  const headers = previewLines[0] ?? "";
  const sampleRows = previewLines.slice(1, 31).join("\n");

  const preview = [
    `CSV file: ${fileName}`,
    `Detected columns: ${headers}`,
    "",
    "Sample rows:",
    sampleRows || "[No sample rows found]",
    "",
    "Raw CSV preview:",
    previewLines.join("\n"),
  ].join("\n");

  assertReadableExtraction(preview, fileName);

  return preview;
}

export async function extractDocumentText(
  file: File,
): Promise<ExtractedDocumentText> {
  const kind = getDocumentKind(file);

  if (!isSupportedIndexFile(file)) {
    throw new Error(
      "Only PDF, DOCX, TXT, MD, and CSV files can be indexed in Phase 2A.",
    );
  }

  const arrayBuffer = await file.arrayBuffer();
  const buffer = Buffer.from(arrayBuffer);

  if (kind === "pdf") {
    const result = await extractPdfText(buffer, file.name);

    return {
      kind,
      text: result.text,
      pageCount: result.pageCount,
    };
  }

  if (kind === "docx") {
    const result = await extractDocxText(buffer, file.name);

    return {
      kind,
      text: result.text,
      pageCount: result.pageCount,
    };
  }

  if (kind === "csv") {
    return {
      kind,
      text: buildCsvText(await file.text(), file.name),
      pageCount: undefined,
    };
  }

  const text = await file.text();
  assertReadableExtraction(text, file.name);

  return {
    kind,
    text,
    pageCount: undefined,
  };
}