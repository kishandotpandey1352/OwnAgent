import type { PremiumInferenceInput } from "./types";
import { estimateTokens } from "./observability";

const DEFAULT_MAX_PROMPT_CHARS = 12000;
const DEFAULT_MAX_CONTEXT_CHARS = 20000;
const DEFAULT_MAX_OUTPUT_TOKENS = 1024;
const DEFAULT_MAX_ESTIMATED_INPUT_TOKENS = 8000;

function numberFromEnv(name: string, fallback: number) {
  const value = process.env[name];

  if (!value) {
    return fallback;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export function validatePremiumInput(input: PremiumInferenceInput) {
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

  const prompt = input.prompt?.trim() ?? "";
  const context = input.context?.trim() ?? "";

  if (!prompt) {
    throw new Error("Prompt is required");
  }

  if (prompt.length > maxPromptChars) {
    throw new Error(
      `Prompt is too long. Limit is ${maxPromptChars} characters.`,
    );
  }

  if (context.length > maxContextChars) {
    throw new Error(
      `Context is too long. Limit is ${maxContextChars} characters.`,
    );
  }

  const estimatedInputTokens = estimateTokens(`${prompt}\n${context}`);

  if (estimatedInputTokens > maxEstimatedInputTokens) {
    throw new Error(
      `Estimated input tokens exceed limit. Limit is ${maxEstimatedInputTokens}.`,
    );
  }

  if ((input.maxNewTokens ?? 0) > maxOutputTokens) {
    throw new Error(
      `Requested output tokens exceed limit. Limit is ${maxOutputTokens}.`,
    );
  }
}

export function applyPremiumDefaults(input: PremiumInferenceInput) {
  const maxOutputTokens = numberFromEnv(
    "PREMIUM_MAX_OUTPUT_TOKENS",
    DEFAULT_MAX_OUTPUT_TOKENS,
  );

  return {
    ...input,
    temperature: Math.min(Math.max(input.temperature ?? 0.2, 0), 1),
    maxNewTokens: Math.min(
      input.maxNewTokens ?? 512,
      maxOutputTokens,
    ),
  };
}