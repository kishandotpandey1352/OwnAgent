import { NextRequest, NextResponse } from "next/server";

import { runPremiumInference, validatePremiumInput } from "../../premium/router";
import { PremiumInferenceInput } from "../types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as PremiumInferenceInput;
    const result = await runPremiumInference(body);

    return NextResponse.json({
      ok: true,
      ...result,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Premium inference failed";

    const requestIdMatch = message.match(/\[([^\]]+)\]/);
    const requestId = requestIdMatch?.[1];

    return NextResponse.json(
      {
        ok: false,
        request_id: requestId,
        error: message,
      },
      { status: 400 },
    );
  }
}