import type { PremiumProviderConfig, PremiumProviderId } from "./types";

export const premiumProviders: Record<PremiumProviderId, PremiumProviderConfig> = {
  "finance-eks": {
    id: "finance-eks",
    name: "Finance EKS 3B",
    provider: "finance-eks",
    modelId: "qwen2.5-3b-finance-runB-r16-lr2e4",
    tier: "premium",
    costClass: "self-hosted",
    privacy: "internal",
    enabled: true,
  },

  "openai-premium": {
    id: "openai-premium",
    name: "OpenAI Premium",
    provider: "openai",
    modelId: process.env.OPENAI_PREMIUM_MODEL ?? "gpt-4.1-mini",
    tier: "premium",
    costClass: "paid-api",
    privacy: "external-provider",
    enabled: Boolean(process.env.OPENAI_API_KEY),
  },

  "claude-premium": {
    id: "claude-premium",
    name: "Claude Premium",
    provider: "anthropic",
    modelId: process.env.ANTHROPIC_PREMIUM_MODEL ?? "claude-sonnet-4-5",
    tier: "premium",
    costClass: "paid-api",
    privacy: "external-provider",
    enabled: Boolean(process.env.ANTHROPIC_API_KEY),
  },

  "gemini-premium": {
    id: "gemini-premium",
    name: "Gemini Premium",
    provider: "gemini",
    modelId: process.env.GEMINI_PREMIUM_MODEL ?? "gemini-2.5-flash",
    tier: "premium",
    costClass: "paid-api",
    privacy: "external-provider",
    enabled: Boolean(process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY),
  },

  "bedrock-premium": {
    id: "bedrock-premium",
    name: "Amazon Bedrock Premium",
    provider: "bedrock",
    modelId: process.env.BEDROCK_MODEL_ID ?? "us.amazon.nova-micro-v1:0",
    tier: "premium",
    costClass: "aws-managed",
    privacy: "aws-managed",
    enabled: Boolean(process.env.BEDROCK_MODEL_ID),
  },

  "vllm-qwen-7b": {
    id: "vllm-qwen-7b",
    name: "Self-hosted vLLM Qwen 7B",
    provider: "vllm",
    modelId: process.env.VLLM_MODEL_ID ?? "Qwen/Qwen2.5-7B-Instruct",
    tier: "premium",
    costClass: "self-hosted",
    privacy: "internal",
    enabled: false,
  },

  "ollama-local": {
    id: "ollama-local",
    name: "Ollama Local",
    provider: "ollama",
    modelId: process.env.OLLAMA_MODEL_ID ?? "llama3.1",
    tier: "premium",
    costClass: "free-local",
    privacy: "internal",
    enabled: false,
  },
};

export function getPremiumProvider(providerId: string) {
  return premiumProviders[providerId as PremiumProviderId];
}

export function listPremiumProviders() {
  return Object.values(premiumProviders);
}