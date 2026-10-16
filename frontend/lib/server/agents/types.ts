export type GroundingConfidence = "high" | "medium" | "low";

export type GroundedAnswerValidation = {
  confidence: GroundingConfidence;
  citedSourceNumbers: number[];
  unsupportedClaims: string[];
  shouldRefuse: boolean;
  reason: string | null;
};

export type GroundedSourceForValidation = {
  sourceNumber: number;
  fileName: string;
  snippet: string;
  score?: number;
};