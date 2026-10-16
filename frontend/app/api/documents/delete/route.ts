import { NextResponse } from "next/server";
import { getConfiguredVectorStore } from "@/lib/server/documents/store-factory";
import { writeRagAuditEvent } from "@/lib/server/documents/audit";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

export async function DELETE(request: Request) {
  const requestId = crypto.randomUUID();
  const userId = getUserId(request);

  try {
    const body = await request.json().catch(() => null);
    const documentId = body?.documentId;

    if (!documentId || typeof documentId !== "string") {
      return NextResponse.json(
        {
          ok: false,
          error: "documentId is required.",
          requestId,
        },
        { status: 400 },
      );
    }

    const store = await getConfiguredVectorStore();

    await store.deleteDocument(userId, documentId);

    await writeRagAuditEvent({
      userId,
      eventType: "document_deleted",
      documentId,
      metadata: {
        cascadeDeleteExpected: true,
      },
  });

    console.info(
      JSON.stringify({
        event: "rag_document_deleted",
        requestId,
        userId,
        documentId,
        timestamp: new Date().toISOString(),
      }),
    );

    return NextResponse.json({
      ok: true,
      documentId,
      requestId,
    });
  } catch (error) {
    console.error(
      JSON.stringify({
        event: "rag_document_delete_failed",
        requestId,
        userId,
        error: error instanceof Error ? error.message : String(error),
        timestamp: new Date().toISOString(),
      }),
    );

    return NextResponse.json(
      {
        ok: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to delete document.",
        requestId,
      },
      { status: 500 },
    );
  }
}