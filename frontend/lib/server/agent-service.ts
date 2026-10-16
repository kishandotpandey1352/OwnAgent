export function getAgentServiceUrl() {
  return process.env.AGENT_SERVICE_URL ?? "http://localhost:8010";
}

export function getUserId(request: Request) {
  return request.headers.get("x-user-id") ?? "local-demo-user";
}

export async function parseAgentServiceResponse(response: Response) {
  const text = await response.text();

  try {
    return JSON.parse(text) as unknown;
  } catch {
    return {
      ok: false,
      error: text || "Agent service returned a non-JSON response.",
    };
  }
}