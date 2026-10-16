import { NextResponse } from "next/server";

import {
  getAgentServiceUrl,
  getUserId,
  parseAgentServiceResponse,
} from "../../../../lib/server/agent-service";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const requestId = crypto.randomUUID();

  try {
    const body = await request.json();

    const response = await fetch(`${getAgentServiceUrl()}/memory/delete`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-user-id": getUserId(request),
      },
      body: JSON.stringify(body),
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
            : "Failed to delete memory through agent service.",
      },
      { status: 502 },
    );
  }
}