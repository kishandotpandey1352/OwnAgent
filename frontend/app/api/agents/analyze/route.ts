import { NextResponse } from "next/server";

import {
  getAgentServiceUrl,
  getUserId,
  parseAgentServiceResponse,
} from "@/lib/server/agent-service";


export const runtime = "nodejs";

export const dynamic = "force-dynamic";


const MAX_TRUSTED_WEB_DOMAINS = 10;


/**
 * Normalize trusted domains before forwarding them to
 * the Python agent service.
 *
 * Examples:
 *
 *   "https://SEC.GOV/"
 *       -> "sec.gov"
 *
 *   "octavegroup.com/path"
 *       -> "octavegroup.com"
 *
 * Duplicate domains are removed.
 */
function normalizeTrustedDomains(
  value: unknown,
): string[] {
  if (
    !Array.isArray(value)
  ) {
    return [];
  }

  const normalized = (
    value
      .filter(
        (
          item: unknown,
        ): item is string =>
          typeof item === "string",
      )
      .map(
        (
          item,
        ) =>
          item
            .trim()
            .toLowerCase(),
      )
      .map(
        (
          item,
        ) =>
          item
            .replace(
              /^https?:\/\//,
              "",
            )
            .replace(
              /\/+$/,
              "",
            ),
      )
      .map(
        (
          item,
        ) =>
          item.split(
            "/",
            1,
          )[0],
      )
      .filter(Boolean)
  );

  return Array.from(
    new Set(
      normalized,
    ),
  ).slice(
    0,
    MAX_TRUSTED_WEB_DOMAINS,
  );
}


/**
 * POST /api/agents/analyze
 *
 * Next.js API gateway for the FastAPI agent service.
 *
 * Phase 3H-F-D:
 *
 * - Web fallback defaults to OFF.
 * - Only literal boolean `true` enables it.
 * - Trusted domains are normalized and capped.
 * - Sanitized values override anything received from
 *   the browser before forwarding to FastAPI.
 */
export async function POST(
  request: Request,
) {
  const requestId =
    crypto.randomUUID();

  try {
    const body =
      (await request.json()) as Record<
        string,
        unknown
      >;

    // =====================================================
    // Phase 3H-F-D
    // Explicit web permission
    // =====================================================

    // Secure default:
    //
    // undefined       -> false
    // null            -> false
    // "true"          -> false
    // 1               -> false
    // true            -> true
    //
    // This prevents accidental coercion from enabling
    // public web research.
    const allowWebFallback =
      body.allow_web_fallback
      === true;

    // =====================================================
    // Phase 3H-F-B / F-D
    // Trusted-domain request hardening
    // =====================================================

    const trustedWebDomains =
      normalizeTrustedDomains(
        body.trusted_web_domains,
      );

    // =====================================================
    // Build sanitized FastAPI request
    // =====================================================

    const agentRequest = {
      ...body,

      // Explicit sanitized override.
      allow_web_fallback:
        allowWebFallback,

      // Explicit sanitized override.
      trusted_web_domains:
        trustedWebDomains,
    };

    // =====================================================
    // Forward to Python agent service
    // =====================================================

    const response =
      await fetch(
        `${getAgentServiceUrl()}/agents/analyze`,
        {
          method:
            "POST",

          headers: {
            "Content-Type":
              "application/json",

            "x-user-id":
              getUserId(
                request,
              ),
          },

          body:
            JSON.stringify(
              agentRequest,
            ),

          // Never let Next.js cache agent responses.
          cache:
            "no-store",
        },
      );

    const payload =
      await parseAgentServiceResponse(
        response,
      );

    // =====================================================
    // Return agent response
    // =====================================================

    return NextResponse.json(
      {
        requestId,

        ...(
          typeof payload
            === "object"
          && payload
            !== null
            ? payload
            : {}
        ),
      },

      {
        status:
          response.status,
      },
    );
  }
  catch (
    error
  ) {
    return NextResponse.json(
      {
        ok:
          false,

        requestId,

        error:
          error
            instanceof Error
            ? error.message
            : (
              "Failed to reach "
              + "agent analysis service."
            ),
      },

      {
        status:
          502,
      },
    );
  }
}