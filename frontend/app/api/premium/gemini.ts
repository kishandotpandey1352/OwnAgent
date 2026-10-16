import { buildTaskPrompt } from "./prompt";
import type { PremiumInferenceInput, PremiumInferenceOutput } from "./types";

type GeminiResponsePayload = {
  candidates?: Array<{
    content?: {
      parts?: Array<{
        text?: string;
      }>;
    };
    finishReason?: string;
  }>;
  usageMetadata?: {
    promptTokenCount?: number;
    candidatesTokenCount?: number;
    totalTokenCount?: number;
  };
  error?: {
    message?: string;
  };
};

function extractGeminiOutput(payload: GeminiResponsePayload) {
  return (
    payload.candidates?.[0]?.content?.parts
      ?.map((part) => part.text ?? "")
      .filter(Boolean)
      .join("\n")
      .trim() ?? ""
  );
}

export async function callGemini(
  input: PremiumInferenceInput,
  startedAt: number,
): Promise<PremiumInferenceOutput> {
  const apiKey = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;

  if (!apiKey) {
    throw new Error("GEMINI_API_KEY is not configured");
  }

  const model = process.env.GEMINI_PREMIUM_MODEL ?? "gemini-2.5-flash";
  const prompt = buildTaskPrompt(input);

  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-goog-api-key": apiKey,
      },
      body: JSON.stringify({
        contents: [
          {
            role: "user",
            parts: [
              {
                text: prompt,
              },
            ],
          },
        ],
        generationConfig: {
          temperature: input.temperature ?? 0.2,
          maxOutputTokens: input.maxNewTokens ?? 512,
        },
      }),
      cache: "no-store",
    },
  );

  const text = await response.text();

  let payload: GeminiResponsePayload;
  try {
    payload = JSON.parse(text) as GeminiResponsePayload;
  } catch {
    throw new Error(text || "Gemini returned a non-JSON response");
  }

  if (!response.ok) {
    throw new Error(payload.error?.message ?? "Gemini request failed");
  }

  const output = extractGeminiOutput(payload);

  return {
    id: `gemini-${Date.now()}`,
    provider: "gemini",
    providerId: input.providerId,
    model_id: model,
    output,
    latency_ms: Math.max(1, Math.round(Date.now() - startedAt)),
    source: "premium",
    usage: {
      prompt_tokens: payload.usageMetadata?.promptTokenCount,
      completion_tokens: payload.usageMetadata?.candidatesTokenCount,
      total_tokens: payload.usageMetadata?.totalTokenCount,
    },
  };
}