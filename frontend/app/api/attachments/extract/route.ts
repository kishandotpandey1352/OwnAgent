import { NextResponse } from "next/server";
import mammoth from "mammoth";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";


type PdfParseResult = {
  text?: string;
  numpages?: number;
};

type PdfParseFunction = (buffer: Buffer) => Promise<PdfParseResult>;

type AttachmentKind = "pdf" | "docx" | "text" | "csv" | "image" | "unknown";

const allowedMimeTypes = new Set([
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
  "text/csv",
  "application/csv",
  "image/png",
  "image/jpeg",
  "image/webp",
]);

function numberFromEnv(name: string, fallback: number) {
  const value = process.env[name];

  if (!value) {
    return fallback;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function getAttachmentKind(file: File): AttachmentKind {
  const name = file.name.toLowerCase();
  const type = file.type;

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

function isAllowedFile(file: File) {
  if (allowedMimeTypes.has(file.type)) {
    return true;
  }

  const name = file.name.toLowerCase();

  return (
    name.endsWith(".pdf") ||
    name.endsWith(".docx") ||
    name.endsWith(".txt") ||
    name.endsWith(".md") ||
    name.endsWith(".csv") ||
    name.endsWith(".png") ||
    name.endsWith(".jpg") ||
    name.endsWith(".jpeg") ||
    name.endsWith(".webp")
  );
}

function truncateText(text: string, maxChars: number) {
  const cleaned = text.replace(/\u0000/g, "").replace(/[ \t]+\n/g, "\n").trim();

  if (cleaned.length <= maxChars) {
    return {
      text: cleaned,
      truncated: false,
    };
  }

  return {
    text: `${cleaned.slice(
      0,
      maxChars,
    )}\n\n[Attachment text truncated at ${maxChars} characters.]`,
    truncated: true,
  };
}

async function extractPdfText(buffer: Buffer) {
  const pdfParseModule = await import("pdf-parse/lib/pdf-parse.js");

  const pdfParse = (
    pdfParseModule.default ?? pdfParseModule
  ) as PdfParseFunction;

  const result = await pdfParse(buffer);

  return {
    text: result.text ?? "",
    pageCount: result.numpages ?? undefined,
  };
}

async function extractDocxText(buffer: Buffer) {
  const result = await mammoth.extractRawText({ buffer });

  return {
    text: result.value ?? "",
    warnings:
      result.messages?.map((message: { message: string }) => message.message) ??
      [],
  };
}

function buildCsvPreview(text: string) {
  const lines = text.split(/\r?\n/).filter(Boolean);
  const maxLines = 200;

  return lines.slice(0, maxLines).join("\n");
}
export async function POST(request: Request) {
  const requestId = `att-${crypto.randomUUID()}`;
  const maxBytes = numberFromEnv("MAX_ATTACHMENT_BYTES", 10 * 1024 * 1024);
  const maxExtractedChars = numberFromEnv("MAX_EXTRACTED_CHARS", 50000);

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
    const kind = getAttachmentKind(file);

    if (!isAllowedFile(file) || kind === "unknown") {
      return NextResponse.json(
        {
          ok: false,
          request_id: requestId,
          error:
            "Unsupported file type. Supported files: PDF, DOCX, TXT, MD, CSV, PNG, JPG, JPEG, WEBP.",
        },
        { status: 400 },
      );
    }

    if (file.size > maxBytes) {
      return NextResponse.json(
        {
          ok: false,
          request_id: requestId,
          error: `File is too large. Limit is ${Math.round(
            maxBytes / 1024 / 1024,
          )} MB.`,
        },
        { status: 400 },
      );
    }

    if (kind === "image") {
      return NextResponse.json({
        ok: true,
        request_id: requestId,
        attachment: {
          id: requestId,
          name: file.name,
          type: file.type,
          size: file.size,
          kind,
          text: "",
          pageCount: undefined,
          truncated: false,
          note:
            "Image upload received. Screenshot/vision extraction will be added in Phase 1B.",
        },
      });
    }

    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    let extractedText = "";
    let pageCount: number | undefined;
    let warnings: string[] = [];

    if (kind === "pdf") {
      const result = await extractPdfText(buffer);
      extractedText = result.text;
      pageCount = result.pageCount;
    }

    if (kind === "docx") {
      const result = await extractDocxText(buffer);
      extractedText = result.text;
      warnings = result.warnings;
    }

    if (kind === "text") {
      extractedText = await file.text();
    }

    if (kind === "csv") {
      extractedText = buildCsvPreview(await file.text());
    }

    const truncated = truncateText(extractedText, maxExtractedChars);

    console.info(
      JSON.stringify({
        event: "attachment_extracted",
        requestId,
        fileName: file.name,
        fileType: file.type,
        fileSize: file.size,
        kind,
        extractedChars: truncated.text.length,
        truncated: truncated.truncated,
        pageCount,
        timestamp: new Date().toISOString(),
      }),
    );

    return NextResponse.json({
      ok: true,
      request_id: requestId,
      attachment: {
        id: requestId,
        name: file.name,
        type: file.type,
        size: file.size,
        kind,
        text: truncated.text,
        pageCount,
        truncated: truncated.truncated,
        warnings,
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Attachment extraction failed.";

    console.error(
      JSON.stringify({
        event: "attachment_extract_failed",
        requestId,
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