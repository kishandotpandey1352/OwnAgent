import { NextResponse } from "next/server";

import { getConfiguredVectorStore } from "@/lib/server/documents/store-factory";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

export async function GET(request: Request) {
  const userId = getUserId(request);
  const store = await getConfiguredVectorStore();
  const documents = await store.listDocuments(userId);

  return NextResponse.json({
    ok: true,
    documents,
  });
}
