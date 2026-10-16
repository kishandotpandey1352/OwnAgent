import { NextRequest, NextResponse } from "next/server";

const AGENT_SERVICE_URL =
  process.env.AGENT_SERVICE_URL ??
  "http://127.0.0.1:8010";

type RouteParams =
  | {
      documentId: string;
    }
  | Promise<{
      documentId: string;
    }>;

export async function GET(
  request: NextRequest,
  context: {
    params: RouteParams;
  },
) {
  const {
    documentId,
  } = await context.params;

  const searchParams =
    request.nextUrl.searchParams;

  const status =
    searchParams.get("status") ??
    "validated";

  const limit =
    searchParams.get("limit") ??
    "250";

  const offset =
    searchParams.get("offset") ??
    "0";

  const userId =
    request.headers.get("x-user-id") ??
    "local-demo-user";

  const upstream =
    new URL(
      `/facts/documents/${encodeURIComponent(
        documentId,
      )}`,
      AGENT_SERVICE_URL,
    );

  upstream.searchParams.set(
    "status",
    status,
  );

  upstream.searchParams.set(
    "limit",
    limit,
  );

  upstream.searchParams.set(
    "offset",
    offset,
  );

  try {
    const response = await fetch(
      upstream,
      {
        method: "GET",
        headers: {
          "X-User-Id": userId,
        },
        cache: "no-store",
      },
    );

    const body =
      await response.json();

    return NextResponse.json(
      body,
      {
        status: response.status,
      },
    );
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error:
          error instanceof Error
            ? error.message
            : "Unable to reach agent service.",
      },
      {
        status: 502,
      },
    );
  }
}