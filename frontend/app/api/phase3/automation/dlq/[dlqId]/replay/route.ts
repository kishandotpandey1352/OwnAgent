import { NextRequest, NextResponse } from "next/server";
import { getPhase3Principal, phase3BackendHeaders, phase3Unauthorized } from "@/lib/server/phase3-principal";

const base = () => process.env.AGENT_SERVICE_URL || process.env.NEXT_PUBLIC_AGENT_SERVICE_URL || "http://127.0.0.1:8010";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ dlqId: string }> },
) {
  const principal = getPhase3Principal(request);
  if (!principal) return phase3Unauthorized();
  const { dlqId } = await params;
  const response = await fetch(`${base()}/automation/dlq/${encodeURIComponent(dlqId)}/replay`, {
    method: "POST",
    headers: phase3BackendHeaders(principal),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
