import { buildTaskPrompt } from "./prompt";
import type { PremiumInferenceInput, PremiumInferenceOutput } from "./types";

type FinanceEksResponse = {
  model_id: string;
  output: string;
};

function getEndpoint(task: PremiumInferenceInput["task"]) {
  if (task === "summarize") {
    return "summarize";
  }

  if (task === "qa") {
    return "qa";
  }

  return "risk-analysis";
}

function buildFinanceEksBody(input: PremiumInferenceInput) {
  const maxNewTokens = input.maxNewTokens ?? 512;
  const temperature = input.temperature ?? 0.2;

  if (input.task === "qa") {
    return {
      question: input.prompt,
      context: input.context ?? "",
      max_new_tokens: maxNewTokens,
      temperature,
    };
  }

  return {
    text: buildTaskPrompt(input),
    max_new_tokens: maxNewTokens,
    temperature,
  };
}

export async function callFinanceEks(
  input: PremiumInferenceInput,
  startedAt: number,
): Promise<PremiumInferenceOutput> {
  const baseUrl = process.env.FINANCE_BACKEND_API_URL ?? "http://localhost:8008";
  const apiKey = process.env.FINANCE_BACKEND_API_KEY ?? "dev-finance-api-key";
  const endpoint = getEndpoint(input.task);

  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/${endpoint}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify(buildFinanceEksBody(input)),
    cache: "no-store",
  });

  const text = await response.text();

  if (!response.ok) {
    throw new Error(text || `Finance EKS request failed with status ${response.status}`);
  }

  const payload = JSON.parse(text) as FinanceEksResponse;

  return {
    id: `premium-${Date.now()}`,
    provider: "finance-eks",
    providerId: input.providerId,
    model_id: payload.model_id,
    output: payload.output,
    latency_ms: Math.max(1, Math.round(Date.now() - startedAt)),
    source: "premium",
  };
}