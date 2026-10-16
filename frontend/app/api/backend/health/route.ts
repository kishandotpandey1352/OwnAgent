import { NextResponse } from "next/server";

const backendBaseUrl = process.env.FINANCE_BACKEND_API_URL ?? "http://localhost:8008";

export async function GET() {
  try {
    const response = await fetch(`${backendBaseUrl.replace(/\/$/, "")}/health`, {
      method: "GET",
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
        error: error instanceof Error ? error.message : "Failed to reach backend /health",
      },
      { status: 502 },
    );
  }
}
