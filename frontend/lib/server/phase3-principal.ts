import { NextRequest, NextResponse } from "next/server";

export type Phase3Principal = {
  userId: string;
  tenantId: string | null;
  roles: string[];
  auditRole: "user" | "analyst" | "auditor" | "administrator";
};

/**
 * Phase 3 BFF identity adapter.
 *
 * Production must populate x-auth-* from the application's authenticated
 * server-side session/middleware. Do not accept browser-provided role claims as
 * authority at the edge. A local administrator principal is available only
 * behind an explicit non-production opt-in for development of the dashboards.
 */
export function getPhase3Principal(request: NextRequest): Phase3Principal | null {
  let userId = request.headers.get("x-auth-user-id")?.trim() || "";
  let tenantId = request.headers.get("x-auth-tenant-id")?.trim() || "";
  let roles = (request.headers.get("x-auth-roles") || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);

  const allowDev =
    process.env.NODE_ENV !== "production" &&
    process.env.PHASE3_ALLOW_DEV_PRINCIPAL === "true";

  if (!userId && allowDev) {
    userId = "local-phase3-admin";
    tenantId = tenantId || "local-demo-tenant";
    roles = ["administrator", "approver", "automation_admin"];
  }

  if (!userId) {
    return null;
  }

  let auditRole: Phase3Principal["auditRole"] = "user";
  if (roles.includes("administrator") || roles.includes("automation_admin")) {
    auditRole = "administrator";
  } else if (roles.includes("auditor")) {
    auditRole = "auditor";
  } else if (roles.includes("analyst")) {
    auditRole = "analyst";
  }

  return {
    userId,
    tenantId: tenantId || null,
    roles,
    auditRole,
  };
}

export function phase3BackendHeaders(principal: Phase3Principal): Record<string, string> {
  const headers: Record<string, string> = {
    "x-user-id": principal.userId,
    "x-audit-role": principal.auditRole,
    "x-roles": principal.roles.join(","),
  };
  if (principal.tenantId) {
    headers["x-tenant-id"] = principal.tenantId;
  }
  return headers;
}

export function phase3Unauthorized() {
  return NextResponse.json(
    {
      error: "Phase 3 dashboard requires an authenticated server-side principal.",
    },
    { status: 401 },
  );
}
