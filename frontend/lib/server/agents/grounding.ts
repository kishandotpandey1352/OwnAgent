import { runPremiumInference } from "@/app/api/premium/router";
import type {
  GroundedAnswerValidation,
  GroundedSourceForValidation,
} from "./types";

type ValidateGroundedAnswerInput = {
  question: string;
  answer: string;
  sources: GroundedSourceForValidation[];
  providerId?: string;
};

function safeJsonParse(value: string): GroundedAnswerValidation {
  try {
    const parsed = JSON.parse(value) as Partial<GroundedAnswerValidation>;

    return {
      confidence:
        parsed.confidence === "high" ||
        parsed.confidence === "medium" ||
        parsed.confidence === "low"
          ? parsed.confidence
          : "low",
      citedSourceNumbers: Array.isArray(parsed.citedSourceNumbers)
        ? parsed.citedSourceNumbers.filter((item) => typeof item === "number")
        : [],
      unsupportedClaims: Array.isArray(parsed.unsupportedClaims)
        ? parsed.unsupportedClaims.filter((item) => typeof item === "string")
        : [],
      shouldRefuse: Boolean(parsed.shouldRefuse),
      reason: typeof parsed.reason === "string" ? parsed.reason : null,
    };
  } catch {
    return {
      confidence: "low",
      citedSourceNumbers: [],
      unsupportedClaims: [
        "The validation response could not be parsed as structured JSON.",
      ],
      shouldRefuse: true,
      reason: "Validation failed.",
    };
  }
}

function buildValidationPrompt(input: ValidateGroundedAnswerInput) {
  const sourcesText = input.sources
    .map(
      (source) =>
        `Source ${source.sourceNumber}\nFile: ${source.fileName}\nSnippet:\n${source.snippet}`,
    )
    .join("\n\n---\n\n");

  return `
You are a strict finance answer validator.

Your job is to check whether the answer is supported ONLY by the provided sources.

Question:
${input.question}

Answer to validate:
${input.answer}

Sources:
${sourcesText}

Return ONLY valid JSON with this exact shape:
{
  "confidence": "high" | "medium" | "low",
  "citedSourceNumbers": number[],
  "unsupportedClaims": string[],
  "shouldRefuse": boolean,
  "reason": string | null
}

Rules:
- Mark confidence high only if the answer is clearly supported by the sources.
- Mark confidence medium if the answer is mostly supported but has minor gaps.
- Mark confidence low if important claims are missing, vague, or unsupported.
- Put unsupported claims in unsupportedClaims.
- Set shouldRefuse true if the answer relies on facts not present in the sources.
- Do not use outside knowledge.
- Do not add markdown.
`.trim();
}

export async function validateGroundedAnswer(
  input: ValidateGroundedAnswerInput,
): Promise<GroundedAnswerValidation> {
  if (!input.sources.length) {
    return {
      confidence: "low",
      citedSourceNumbers: [],
      unsupportedClaims: ["No retrieved sources were available."],
      shouldRefuse: true,
      reason: "No evidence was retrieved.",
    };
  }

  const validationPrompt = buildValidationPrompt(input);
  const providerId = input.providerId ?? "openai-premium";

  const result = await runPremiumInference({
    providerId: providerId as Parameters<typeof runPremiumInference>[0]["providerId"],
    task: "qa",
    prompt: validationPrompt,
    context: "",
    temperature: 0,
    maxNewTokens: 500,
  });

  return safeJsonParse(result.output ?? "");
}