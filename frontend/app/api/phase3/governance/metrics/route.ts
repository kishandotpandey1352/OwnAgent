import { NextRequest, NextResponse } from "next/server";
import { getPhase3Principal, phase3BackendHeaders, phase3Unauthorized } from "@/lib/server/phase3-principal";

const base = () => process.env.AGENT_SERVICE_URL || process.env.NEXT_PUBLIC_AGENT_SERVICE_URL || "http://127.0.0.1:8010";

export async function GET(request: NextRequest) {
  const principal = getPhase3Principal(request);
  if (!principal) return phase3Unauthorized();
  const response = await fetch(`${base()}/governance/metrics`, {
    cache: "no-store",
    headers: phase3BackendHeaders(principal),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
