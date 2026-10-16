import { buildTaskPrompt } from "./prompt";
import type { PremiumInferenceInput, PremiumInferenceOutput } from "./types";

type AnthropicResponsePayload = {
  id?: string;
  content?: Array<{
    type?: string;
    text?: string;
  }>;
  usage?: {
    input_tokens?: number;
    output_tokens?: number;
  };
  error?: {
    message?: string;
  };
};

function extractAnthropicOutput(payload: AnthropicResponsePayload) {
  return (
    payload.content
      ?.map((block) => block.text ?? "")
      .filter(Boolean)
      .join("\n")
      .trim() ?? ""
  );
}

export async function callAnthropic(
  input: PremiumInferenceInput,
  startedAt: number,
): Promise<PremiumInferenceOutput> {
  const apiKey = process.env.ANTHROPIC_API_KEY;

  if (!apiKey) {
    throw new Error("ANTHROPIC_API_KEY is not configured");
  }

  const model = process.env.ANTHROPIC_PREMIUM_MODEL ?? "claude-sonnet-4-5";
  const prompt = buildTaskPrompt(input);

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model,
      max_tokens: input.maxNewTokens ?? 512,
      temperature: input.temperature ?? 0.2,
      messages: [
        {
          role: "user",
          content: prompt,
        },
      ],
    }),
    cache: "no-store",
  });

  const text = await response.text();

  let payload: AnthropicResponsePayload;
  try {
    payload = JSON.parse(text) as AnthropicResponsePayload;
  } catch {
    throw new Error(text || "Anthropic returned a non-JSON response");
  }

  if (!response.ok) {
    throw new Error(payload.error?.message ?? "Anthropic request failed");
  }

  const output = extractAnthropicOutput(payload);

  return {
    id: payload.id ?? `anthropic-${Date.now()}`,
    provider: "anthropic",
    providerId: input.providerId,
    model_id: model,
    output,
    latency_ms: Math.max(1, Math.round(Date.now() - startedAt)),
    source: "premium",
    usage: {
      prompt_tokens: payload.usage?.input_tokens,
      completion_tokens: payload.usage?.output_tokens,
      total_tokens:
        payload.usage?.input_tokens && payload.usage?.output_tokens
          ? payload.usage.input_tokens + payload.usage.output_tokens
          : undefined,
    },
  };
}