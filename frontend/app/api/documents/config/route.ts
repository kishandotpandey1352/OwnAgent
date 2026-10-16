import { NextResponse } from "next/server";

import {
  buildConfigForProfile,
  disabledProfiles,
  getEnabledProfiles,
  readRagConfig,
  writeRagConfig,
} from "@/lib/server/documents/config";
import type { DocumentStorageProfile } from "@/lib/server/documents/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type ConfigBody = {
  profile?: DocumentStorageProfile;
};

export async function GET() {
  const config = await readRagConfig();

  return NextResponse.json({
    ok: true,
    config,
    enabledProfiles: getEnabledProfiles(),
    disabledProfiles,
  });
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as ConfigBody;
    const currentConfig = await readRagConfig();

    if (!body.profile) {
      return NextResponse.json(
        {
          ok: false,
          error: "profile is required.",
        },
        { status: 400 },
      );
    }

    const nextConfig = buildConfigForProfile(body.profile, currentConfig);

    const reindexRequired =
      nextConfig.embeddingModel !== currentConfig.embeddingModel ||
      nextConfig.vectorStorage !== currentConfig.vectorStorage;

    await writeRagConfig(nextConfig);

    return NextResponse.json({
      ok: true,
      config: nextConfig,
      warnings: reindexRequired
        ? [
            "Changing embedding model or vector storage requires re-indexing existing documents.",
          ]
        : [],
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to update RAG config.";

    return NextResponse.json(
      {
        ok: false,
        error: message,
      },
      { status: 400 },
    );
  }
}