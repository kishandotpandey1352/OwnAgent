import type { PremiumInferenceInput } from "./types";

export function buildTaskPrompt(input: PremiumInferenceInput) {
  const prompt = input.prompt.trim();
  const context = input.context?.trim();

  if (input.task === "summarize") {
    return context
      ? `Summarize the following financial text.

Text:
${prompt}

Instructions:
${context}`
      : `Summarize the following financial text.

Text:
${prompt}`;
  }

  if (input.task === "qa") {
    return `Answer the question using only the provided context.

Question:
${prompt}

Context:
${context ?? ""}`;
  }

  return context
    ? `Analyze the financial risks in the following text.

Text:
${prompt}

Risk focus:
${context}`
    : `Analyze the financial risks in the following text.

Text:
${prompt}`;
}