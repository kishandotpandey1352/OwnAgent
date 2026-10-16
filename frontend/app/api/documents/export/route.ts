import { NextResponse } from "next/server";

import { readRagConfig } from "@/lib/server/documents/config";
import { getConfiguredVectorStore } from "@/lib/server/documents/store-factory";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

export async function GET(request: Request) {
  const userId = getUserId(request);

  const store = await getConfiguredVectorStore();
  const config = await readRagConfig();
  const documents = await store.listDocuments(userId);
  const chunks = await store.getChunksByDocumentIds(
    userId,
    documents.map((document) => document.id),
  );

  return NextResponse.json({
    ok: true,
    version: "finance-rag-memory-v1",
    exportedAt: new Date().toISOString(),
    userId,
    config,
    documents,
    chunks,
    note:
      "Vectors are not included in this first export endpoint. Re-indexing may be required after import unless vector export is added.",
  });
}