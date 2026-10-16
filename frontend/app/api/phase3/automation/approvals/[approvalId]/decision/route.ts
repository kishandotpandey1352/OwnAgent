import { NextRequest, NextResponse } from "next/server";
import { getPhase3Principal, phase3BackendHeaders, phase3Unauthorized } from "@/lib/server/phase3-principal";

const base = () => process.env.AGENT_SERVICE_URL || process.env.NEXT_PUBLIC_AGENT_SERVICE_URL || "http://127.0.0.1:8010";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ approvalId: string }> },
) {
  const principal = getPhase3Principal(request);
  if (!principal) return phase3Unauthorized();
  if (!principal.tenantId) {
    return NextResponse.json({ error: "Approval decisions require tenant identity." }, { status: 403 });
  }
  const { approvalId } = await params;
  const incoming = await request.json();
  const response = await fetch(`${base()}/automation/approvals/${encodeURIComponent(approvalId)}/decision`, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      ...phase3BackendHeaders(principal),
    },
    body: JSON.stringify({ approve: Boolean(incoming.approve) }),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
