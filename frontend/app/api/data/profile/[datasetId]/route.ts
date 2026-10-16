import { NextResponse } from "next/server";

import {
  getAgentServiceUrl,
  getUserId,
  parseAgentServiceResponse,
} from "@/lib/server/agent-service";


export const runtime = "nodejs";
export const dynamic = "force-dynamic";


type RouteContext = {
  params: Promise<{
    datasetId: string;
  }>;
};


export async function GET(
  request: Request,
  context: RouteContext,
) {
  const requestId = crypto.randomUUID();

  try {
    const { datasetId } = await context.params;

    if (!datasetId) {
      return NextResponse.json(
        {
          ok: false,
          requestId,
          error: "Dataset ID is required.",
        },
        {
          status: 400,
        },
      );
    }

    const response = await fetch(
      `${getAgentServiceUrl()}/data/profile/${encodeURIComponent(
        datasetId,
      )}`,
      {
        method: "GET",
        headers: {
          "x-user-id": getUserId(request),
        },
        cache: "no-store",
      },
    );

    const payload =
      await parseAgentServiceResponse(response);

    return NextResponse.json(
      {
        requestId,
        ...(typeof payload === "object" &&
        payload !== null
          ? payload
          : {}),
      },
      {
        status: response.status,
      },
    );
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        requestId,
        error:
          error instanceof Error
            ? error.message
            : "Failed to reach CSV profile service.",
      },
      {
        status: 502,
      },
    );
  }
}