import { buildTaskPrompt } from "./prompt";
import type { PremiumInferenceInput, PremiumInferenceOutput } from "./types";

type OpenAIResponsePayload = {
  id?: string;
  output_text?: string;
  output?: Array<{
    content?: Array<{
      type?: string;
      text?: string;
    }>;
  }>;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
    total_tokens?: number;
  };
  error?: {
    message?: string;
  };
};

function extractOpenAIOutput(payload: OpenAIResponsePayload) {
  if (payload.output_text) {
    return payload.output_text;
  }

  return (
    payload.output
      ?.flatMap((item) => item.content ?? [])
      .map((content) => content.text ?? "")
      .filter(Boolean)
      .join("\n")
      .trim() ?? ""
  );
}

export async function callOpenAI(
  input: PremiumInferenceInput,
  startedAt: number,
): Promise<PremiumInferenceOutput> {
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    throw new Error("OPENAI_API_KEY is not configured");
  }

  const model = process.env.OPENAI_PREMIUM_MODEL ?? "gpt-4.1-mini";
  const prompt = buildTaskPrompt(input);

  const response = await fetch("https://api.openai.com/v1/responses", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      input: prompt,
      temperature: input.temperature ?? 0.2,
      max_output_tokens: input.maxNewTokens ?? 512,
    }),
    cache: "no-store",
  });

  const text = await response.text();

  let payload: OpenAIResponsePayload;
  try {
    payload = JSON.parse(text) as OpenAIResponsePayload;
  } catch {
    throw new Error(text || "OpenAI returned a non-JSON response");
  }

  if (!response.ok) {
    throw new Error(payload.error?.message ?? "OpenAI request failed");
  }

  const output = extractOpenAIOutput(payload);

  return {
    id: payload.id ?? `openai-${Date.now()}`,
    provider: "openai",
    providerId: input.providerId,
    model_id: model,
    output,
    latency_ms: Math.max(1, Math.round(Date.now() - startedAt)),
    source: "premium",
    usage: {
      prompt_tokens: payload.usage?.input_tokens,
      completion_tokens: payload.usage?.output_tokens,
      total_tokens: payload.usage?.total_tokens,
    },
  };
}