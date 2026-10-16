import { NextResponse } from "next/server";
import {
  getAgentServiceUrl,
  getUserId,
  parseAgentServiceResponse,
} from "@/lib/server/agent-service";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";



export async function GET(request: Request) {
  const requestId = crypto.randomUUID();

  try {
    const response = await fetch(`${getAgentServiceUrl()}/memory/list`, {
      method: "GET",
      headers: {
        "x-user-id": getUserId(request),
      },
      cache: "no-store",
    });

    const payload = await parseAgentServiceResponse(response);

    return NextResponse.json(
      {
        requestId,
        ...(typeof payload === "object" && payload !== null ? payload : {}),
      },
      { status: response.status },
    );
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        requestId,
        error:
          error instanceof Error
            ? error.message
            : "Failed to reach agent memory service.",
      },
      { status: 502 },
    );
  }
}