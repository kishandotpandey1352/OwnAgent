import { NextResponse } from "next/server";

import { getConfiguredVectorStore } from "@/lib/server/documents/store-factory";
import { writeRagAuditEvent } from "@/lib/server/documents/audit";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

export async function DELETE(request: Request) {
  const userId = getUserId(request);

  try {
    const store = await getConfiguredVectorStore();
    await store.clearUserMemory(userId);
    
    await writeRagAuditEvent({
        userId,
        eventType: "memory_cleared",
        metadata: {
            cascadeDeleteExpected: true,
        },
    });

    console.info(
      JSON.stringify({
        event: "rag_memory_cleared",
        userId,
        timestamp: new Date().toISOString(),
      }),
    );

    return NextResponse.json({
      ok: true,
      userId,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to clear document memory.";

    return NextResponse.json(
      {
        ok: false,
        error: message,
      },
      { status: 500 },
    );
  }
}
