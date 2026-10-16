import { NextRequest, NextResponse } from "next/server";

const backendBaseUrl = process.env.FINANCE_BACKEND_API_URL ?? "http://localhost:8008";
const backendApiKey = process.env.FINANCE_BACKEND_API_KEY ?? process.env.NEXT_PUBLIC_DEFAULT_API_KEY ?? "dev-finance-api-key";

const allowedEndpoints = new Set(["summarize", "qa", "risk-analysis"]);

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ endpoint: string }> },
) {
  const { endpoint } = await context.params;

  if (!allowedEndpoints.has(endpoint)) {
    return NextResponse.json(
      {
        ok: false,
        error: `Unsupported backend endpoint: ${endpoint}`,
      },
      { status: 404 },
    );
  }

  try {
    const body = await request.json();

    const response = await fetch(`${backendBaseUrl.replace(/\/$/, "")}/${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": backendApiKey,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const text = await response.text();

    if (!response.ok) {
      return NextResponse.json(
        {
          ok: false,
          status: response.status,
          error: text || response.statusText,
        },
        { status: response.status },
      );
    }

    return NextResponse.json(JSON.parse(text));
  } catch (error) {
    return NextResponse.json(
      {
        ok: false,
        error: error instanceof Error ? error.message : "Backend inference request failed",
      },
      { status: 502 },
    );
  }
}
