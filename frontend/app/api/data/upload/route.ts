import { NextResponse } from "next/server";

import {
  getAgentServiceUrl,
  getUserId,
  parseAgentServiceResponse,
} from "@/lib/server/agent-service";


export const runtime = "nodejs";
export const dynamic = "force-dynamic";


export async function POST(request: Request) {
  const requestId = crypto.randomUUID();

  try {
    const formData = await request.formData();
    const file = formData.get("file");

    if (!(file instanceof File)) {
      return NextResponse.json(
        {
          ok: false,
          requestId,
          error: "A CSV file is required.",
        },
        {
          status: 400,
        },
      );
    }

    if (!file.name.toLowerCase().endsWith(".csv")) {
      return NextResponse.json(
        {
          ok: false,
          requestId,
          error: "Only CSV files are supported.",
        },
        {
          status: 415,
        },
      );
    }

    if (file.size === 0) {
      return NextResponse.json(
        {
          ok: false,
          requestId,
          error: "The uploaded CSV is empty.",
        },
        {
          status: 400,
        },
      );
    }

    const upstreamFormData = new FormData();

    upstreamFormData.append(
      "file",
      file,
      file.name,
    );

    const response = await fetch(
      `${getAgentServiceUrl()}/data/upload`,
      {
        method: "POST",
        headers: {
          "x-user-id": getUserId(request),
        },
        body: upstreamFormData,
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
            : "Failed to reach CSV upload service.",
      },
      {
        status: 502,
      },
    );
  }
}