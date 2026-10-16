import { NextResponse } from "next/server";
import { readRagConfig } from "@/lib/server/documents/config";
import { getSupabaseServerClient } from "@/lib/server/documents/stores/supabase-client";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

export async function GET(request: Request) {
  const requestId = crypto.randomUUID();
  const userId = getUserId(request);

  try {
    const config = await readRagConfig();

    if (config.profile !== "supabase-pgvector") {
      return NextResponse.json({
        ok: true,
        events: [],
        requestId,
        note: "Audit events are persisted only for the Supabase document memory profile. Local profiles write audit events to server logs.",
      });
    }

    const supabase = getSupabaseServerClient();

    const { data, error } = await supabase
      .from("rag_audit_events")
      .select(
        "id,user_id,event_type,document_id,file_name,storage_profile,embedding_model,metadata,created_at",
      )
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(50);

    if (error) {
      throw new Error(error.message);
    }

    return NextResponse.json({
      ok: true,
      events: data ?? [],
      requestId,
    });
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error:
          error instanceof Error
            ? error.message
            : "Failed to load document audit events.",
        requestId,
      },
      { status: 500 },
    );
  }
}