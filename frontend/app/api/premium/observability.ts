import type { PremiumInferenceInput, PremiumInferenceOutput } from "./types";

export function createRequestId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }

  return `req-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function nowMs() {
  return Date.now();
}

export function latencyMs(startedAt: number) {
  return Math.max(1, Date.now() - startedAt);
}

export function estimateTokens(text: string) {
  return Math.max(
    1,
    Math.round(text.trim().split(/\s+/).filter(Boolean).length * 1.2),
  );
}

export function normalizeProviderError(error: unknown) {
  if (error instanceof Error) {
    return {
      message: error.message,
      retryable:
        error.message.toLowerCase().includes("timeout") ||
        error.message.toLowerCase().includes("rate") ||
        error.message.toLowerCase().includes("quota") ||
        error.message.toLowerCase().includes("temporarily"),
    };
  }

  return {
    message: "Unknown provider error",
    retryable: false,
  };
}

export function logInferenceStart(params: {
  requestId: string;
  input: PremiumInferenceInput;
}) {
  console.info(
    JSON.stringify({
      event: "premium_inference_started",
      requestId: params.requestId,
      providerId: params.input.providerId,
      task: params.input.task,
      mode: params.input.mode ?? "premium",
      promptChars: params.input.prompt.length,
      contextChars: params.input.context?.length ?? 0,
      temperature: params.input.temperature,
      maxNewTokens: params.input.maxNewTokens,
      timestamp: new Date().toISOString(),
    }),
  );
}

export function logInferenceSuccess(params: {
  requestId: string;
  input: PremiumInferenceInput;
  output: PremiumInferenceOutput;
}) {
  console.info(
    JSON.stringify({
      event: "premium_inference_succeeded",
      requestId: params.requestId,
      providerId: params.input.providerId,
      modelId: params.output.model_id,
      task: params.input.task,
      mode: params.input.mode ?? "premium",
      latencyMs: params.output.latency_ms,
      promptTokens: params.output.usage?.prompt_tokens,
      completionTokens: params.output.usage?.completion_tokens,
      totalTokens: params.output.usage?.total_tokens,
      fallbackUsed: params.output.fallback_used ?? false,
      timestamp: new Date().toISOString(),
    }),
  );
}

export function logInferenceFailure(params: {
  requestId: string;
  input: PremiumInferenceInput;
  error: unknown;
  latencyMs: number;
}) {
  const normalized = normalizeProviderError(params.error);

  console.error(
    JSON.stringify({
      event: "premium_inference_failed",
      requestId: params.requestId,
      providerId: params.input.providerId,
      task: params.input.task,
      mode: params.input.mode ?? "premium",
      latencyMs: params.latencyMs,
      error: normalized.message,
      retryable: normalized.retryable,
      timestamp: new Date().toISOString(),
    }),
  );
}