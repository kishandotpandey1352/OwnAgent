export type PremiumProviderId =
  | "finance-eks"
  | "openai-premium"
  | "claude-premium"
  | "gemini-premium"
  | "bedrock-premium"
  | "vllm-qwen-7b"
  | "ollama-local";

export type PremiumTask = "summarize" | "qa" | "risk-analysis";

export type PremiumInferenceInput = {
  providerId: PremiumProviderId;
  task: PremiumTask;
  mode?: "premium" | "compare";
  prompt: string;
  context?: string;
  temperature?: number;
  maxNewTokens?: number;
};

export type PremiumInferenceOutput = {
  id: string;
  provider: string;
  providerId: PremiumProviderId;
  model_id: string;
  output: string;
  latency_ms: number;
  source: "premium";
  request_id?: string;
  fallback_used?: boolean;
  fallback_from?: PremiumProviderId;
  error?: {
    providerId: PremiumProviderId;
    message: string;
    code?: string;
    retryable?: boolean;
  };
  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
};

export type PremiumProviderConfig = {
  id: PremiumProviderId;
  name: string;
  provider: string;
  modelId: string;
  tier: "premium";
  costClass: "self-hosted" | "paid-api" | "free-local" | "aws-managed";
  privacy: "internal" | "external-provider" | "aws-managed";
  enabled: boolean;
};
