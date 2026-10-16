import { randomUUID } from "crypto";

import { callAnthropic } from "./anthropic";
import { callBedrock } from "./bedrock";
import { callFinanceEks } from "./financeEks";
import { callGemini } from "./gemini";
import { callOpenAI } from "./openai";
import { getPremiumProvider } from "./providers";
import type {
  PremiumInferenceInput,
  PremiumInferenceOutput,
  PremiumProviderId,
} from "./types";

const allowedTasks = new Set(["summarize", "qa", "risk-analysis"]);

const DEFAULT_MAX_PROMPT_CHARS = 12000;
const DEFAULT_MAX_CONTEXT_CHARS = 20000;
const DEFAULT_MAX_OUTPUT_TOKENS = 1024;
const DEFAULT_MAX_ESTIMATED_INPUT_TOKENS = 8000;

function createRequestId() {
  return `req-${randomUUID()}`;
}

function numberFromEnv(name: string, fallback: number) {
  const value = process.env[name];

  if (!value) {
    return fallback;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function latencyMs(startedAt: number) {
  return Math.max(1, Date.now() - startedAt);
}

function estimateTokens(text: string) {
  return Math.max(
    1,
    Math.round(text.trim().split(/\s+/).filter(Boolean).length * 1.2),
  );
}

function normalizeProviderError(error: unknown) {
  if (error instanceof Error) {
    const message = error.message;
    const lowerMessage = message.toLowerCase();

    return {
      message,
      retryable:
        lowerMessage.includes("timeout") ||
        lowerMessage.includes("rate") ||
        lowerMessage.includes("quota") ||
        lowerMessage.includes("token") ||
        lowerMessage.includes("temporarily") ||
        lowerMessage.includes("too many") ||
        lowerMessage.includes("overloaded") ||
        lowerMessage.includes("unavailable"),
    };
  }

  return {
    message: "Unknown provider error",
    retryable: false,
  };
}

function logInferenceStart(params: {
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

function logInferenceSuccess(params: {
  requestId: string;
  input: PremiumInferenceInput;
  output: PremiumInferenceOutput & {
    request_id?: string;
    fallback_used?: boolean;
    fallback_from?: PremiumProviderId;
  };
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
      fallbackFrom: params.output.fallback_from,
      timestamp: new Date().toISOString(),
    }),
  );
}

function logInferenceFailure(params: {
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

function validateGuardrails(value: Partial<PremiumInferenceInput>) {
  const maxPromptChars = numberFromEnv(
    "PREMIUM_MAX_PROMPT_CHARS",
    DEFAULT_MAX_PROMPT_CHARS,
  );
  const maxContextChars = numberFromEnv(
    "PREMIUM_MAX_CONTEXT_CHARS",
    DEFAULT_MAX_CONTEXT_CHARS,
  );
  const maxOutputTokens = numberFromEnv(
    "PREMIUM_MAX_OUTPUT_TOKENS",
    DEFAULT_MAX_OUTPUT_TOKENS,
  );
  const maxEstimatedInputTokens = numberFromEnv(
    "PREMIUM_MAX_ESTIMATED_INPUT_TOKENS",
    DEFAULT_MAX_ESTIMATED_INPUT_TOKENS,
  );

  const prompt = value.prompt?.trim() ?? "";
  const context = value.context?.trim() ?? "";
  const estimatedInputTokens = estimateTokens(`${prompt}\n${context}`);
  const maxNewTokens = value.maxNewTokens ?? 512;

  if (prompt.length > maxPromptChars) {
    throw new Error(
      `Prompt is too large. Limit is ${maxPromptChars} characters.`,
    );
  }

  if (context.length > maxContextChars) {
    throw new Error(
      `Context is too large. Limit is ${maxContextChars} characters.`,
    );
  }

  if (estimatedInputTokens > maxEstimatedInputTokens) {
    throw new Error(
      `Estimated input tokens exceed limit. Limit is ${maxEstimatedInputTokens}.`,
    );
  }

  if (maxNewTokens > maxOutputTokens) {
    throw new Error(
      `Requested output tokens exceed limit. Limit is ${maxOutputTokens}.`,
    );
  }
}

function applyPremiumDefaults(
  input: PremiumInferenceInput,
): PremiumInferenceInput {
  const maxOutputTokens = numberFromEnv(
    "PREMIUM_MAX_OUTPUT_TOKENS",
    DEFAULT_MAX_OUTPUT_TOKENS,
  );

  return {
    ...input,
    temperature: Math.min(Math.max(input.temperature ?? 0.2, 0), 1),
    maxNewTokens: Math.min(input.maxNewTokens ?? 512, maxOutputTokens),
  };
}

export function validatePremiumInput(input: unknown): PremiumInferenceInput {
  const value = input as Partial<PremiumInferenceInput>;

  if (!value.providerId || typeof value.providerId !== "string") {
    throw new Error("providerId is required");
  }

  const provider = getPremiumProvider(value.providerId);

  if (!provider) {
    throw new Error(`Unsupported premium provider: ${value.providerId}`);
  }

  if (!provider.enabled) {
    throw new Error(`Premium provider is not enabled yet: ${value.providerId}`);
  }

  if (!value.task || !allowedTasks.has(value.task)) {
    throw new Error("task must be summarize, qa, or risk-analysis");
  }

  if (!value.prompt || typeof value.prompt !== "string" || !value.prompt.trim()) {
    throw new Error("prompt is required");
  }

  const maxNewTokens = value.maxNewTokens ?? 512;

  if (maxNewTokens < 1 || maxNewTokens > 2048) {
    throw new Error("maxNewTokens must be between 1 and 2048");
  }

  const temperature = value.temperature ?? 0.2;

  if (temperature < 0 || temperature > 1.5) {
    throw new Error("temperature must be between 0 and 1.5");
  }

  validateGuardrails(value);

  return applyPremiumDefaults({
    providerId: value.providerId,
    task: value.task,
    mode: value.mode ?? "premium",
    prompt: value.prompt.trim(),
    context: value.context,
    temperature,
    maxNewTokens,
  });
}

async function callProvider(
  input: PremiumInferenceInput,
  startedAt: number,
): Promise<PremiumInferenceOutput> {
  if (input.providerId === "finance-eks") {
    return callFinanceEks(input, startedAt);
  }

  if (input.providerId === "openai-premium") {
    return callOpenAI(input, startedAt);
  }

  if (input.providerId === "claude-premium") {
    return callAnthropic(input, startedAt);
  }

  if (input.providerId === "gemini-premium") {
    return callGemini(input, startedAt);
  }

  if (input.providerId === "bedrock-premium") {
    return callBedrock(input, startedAt);
  }

  throw new Error(`Provider adapter is not implemented yet: ${input.providerId}`);
}

function getFallbackProviderId(
  providerId: PremiumProviderId,
): PremiumProviderId | null {
  if (process.env.PREMIUM_ENABLE_FALLBACK !== "true") {
    return null;
  }

  if (providerId !== "openai-premium") {
    const openAiProvider = getPremiumProvider("openai-premium");

    if (openAiProvider?.enabled && process.env.OPENAI_API_KEY) {
      return "openai-premium";
    }
  }

  if (providerId !== "claude-premium") {
    const claudeProvider = getPremiumProvider("claude-premium");

    if (claudeProvider?.enabled && process.env.ANTHROPIC_API_KEY) {
      return "claude-premium";
    }
  }

  if (providerId !== "gemini-premium") {
    const geminiProvider = getPremiumProvider("gemini-premium");

    if (
      geminiProvider?.enabled &&
      (process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY)
    ) {
      return "gemini-premium";
    }
  }

  return null;
}

export async function runPremiumInference(
  input: PremiumInferenceInput,
): Promise<
  PremiumInferenceOutput & {
    request_id: string;
    fallback_used: boolean;
    fallback_from?: PremiumProviderId;
  }
> {
  const requestId = createRequestId();
  const startedAt = Date.now();
  const validatedInput = applyPremiumDefaults(input);

  logInferenceStart({
    requestId,
    input: validatedInput,
  });

  try {
    const output = await callProvider(validatedInput, startedAt);

    const finalOutput = {
      ...output,
      request_id: requestId,
      latency_ms: output.latency_ms ?? latencyMs(startedAt),
      fallback_used: false,
    };

    logInferenceSuccess({
      requestId,
      input: validatedInput,
      output: finalOutput,
    });

    return finalOutput;
  } catch (error) {
    logInferenceFailure({
      requestId,
      input: validatedInput,
      error,
      latencyMs: latencyMs(startedAt),
    });

    const fallbackProviderId = getFallbackProviderId(validatedInput.providerId);

    if (!fallbackProviderId) {
      const normalized = normalizeProviderError(error);

      throw new Error(
        `[${requestId}] ${validatedInput.providerId} failed: ${normalized.message}`,
      );
    }

    const fallbackInput: PremiumInferenceInput = {
      ...validatedInput,
      providerId: fallbackProviderId,
    };

    try {
      const fallbackOutput = await callProvider(fallbackInput, startedAt);

      const finalOutput = {
        ...fallbackOutput,
        request_id: requestId,
        latency_ms: fallbackOutput.latency_ms ?? latencyMs(startedAt),
        fallback_used: true,
        fallback_from: validatedInput.providerId,
      };

      logInferenceSuccess({
        requestId,
        input: fallbackInput,
        output: finalOutput,
      });

      return finalOutput;
    } catch (fallbackError) {
      logInferenceFailure({
        requestId,
        input: fallbackInput,
        error: fallbackError,
        latencyMs: latencyMs(startedAt),
      });

      const normalizedOriginal = normalizeProviderError(error);
      const normalizedFallback = normalizeProviderError(fallbackError);

      throw new Error(
        `[${requestId}] ${validatedInput.providerId} failed: ${normalizedOriginal.message}. Fallback ${fallbackProviderId} also failed: ${normalizedFallback.message}`,
      );
    }
  }
}