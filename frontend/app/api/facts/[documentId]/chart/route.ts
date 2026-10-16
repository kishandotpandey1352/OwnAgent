import {
  NextRequest,
  NextResponse,
} from "next/server";


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

  const params =
    request.nextUrl.searchParams;

  const metricKey =
    params.get("metric_key");

  if (!metricKey) {
    return NextResponse.json(
      {
        ok: false,
        error:
          "metric_key is required.",
      },
      {
        status: 400,
      },
    );
  }

  const upstream =
    new URL(
      `/facts/documents/${encodeURIComponent(
        documentId,
      )}/chart`,
      AGENT_SERVICE_URL,
    );

  upstream.searchParams.set(
    "metric_key",
    metricKey,
  );

  upstream.searchParams.set(
    "chart_type",
    params.get(
      "chart_type",
    ) ?? "auto",
  );

  for (
    const key
    of [
      "company",
      "category",
      "statement_type",
    ]
  ) {
    const value =
      params.get(key);

    if (value) {
      upstream.searchParams.set(
        key,
        value,
      );
    }
  }

  const userId =
    request.headers.get(
      "x-user-id",
    ) ??
    "local-demo-user";

  try {
    const response =
      await fetch(
        upstream,
        {
          method: "GET",
          headers: {
            "X-User-Id":
              userId,
          },
          cache: "no-store",
        },
      );

    const body =
      await response.json();

    return NextResponse.json(
      body,
      {
        status:
          response.status,
      },
    );

  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error:
          error instanceof Error
            ? error.message
            : (
              "Unable to reach "
              + "agent service."
            ),
      },
      {
        status: 502,
      },
    );
  }
}