import type { FinanceTask, ProviderOption } from "types/index.ts";

export const tasks: Array<{ value: FinanceTask; label: string; description: string }> = [
  {
    value: "summarize",
    label: "Summarize",
    description: "Condense earnings, filings, or guidance into an executive brief.",
  },
  {
    value: "qa",
    label: "Q&A",
    description: "Answer investor, risk, or operations questions from context.",
  },
  {
    value: "risk-analysis",
    label: "Risk analysis",
    description: "Extract market, credit, liquidity, operational, and business risk.",
  },
];

export const providerCatalog: ProviderOption[] = [
  {
    id: "finance-base",
    name: "Finance Base",
    provider: "finance-eks",
    description: "Baseline self-hosted finance model routed through the secure FastAPI gateway on EKS.",
    tier: "basic",
    modelId: "qwen2.5-3b-base",
    costClass: "self-hosted",
    privacy: "internal",
    latency: "medium",
    defaultTemperature: 0.15,
    defaultMaxNewTokens: 256,
    enabled: true,
  },
  {
    id: "finance-adapter",
    name: "Finance Adapter on EKS",
    provider: "finance-eks",
    description: "Qwen2.5 3B finance LoRA adapter running on AWS EKS through the FastAPI inference backend.",
    tier: "premium",
    modelId: "qwen2.5-3b-finance-runB-r16-lr2e4",
    costClass: "self-hosted",
    privacy: "internal",
    latency: "medium",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 320,
    enabled: true,
  },
  {
    id: "openai-premium",
    name: "OpenAI Premium",
    provider: "openai",
    description: "Paid proprietary provider for strong reasoning and general financial analysis.",
    tier: "premium",
    modelId: "env:OPENAI_PREMIUM_MODEL",
    costClass: "paid-api",
    privacy: "external-provider",
    latency: "low",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 512,
    enabled: true,
  },
  {
    id: "claude-premium",
    name: "Claude Premium",
    provider: "anthropic",
    description: "Paid Anthropic Claude provider, useful for long financial documents and context-heavy Q&A.",
    tier: "premium",
    modelId: "env:ANTHROPIC_PREMIUM_MODEL",
    costClass: "paid-api",
    privacy: "external-provider",
    latency: "low",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 512,
    enabled: true,
  },
  {
    id: "gemini-premium",
    name: "Gemini Premium",
    provider: "gemini",
    description: "Google Gemini provider for multi-provider LLM routing and Google ecosystem coverage.",
    tier: "premium",
    modelId: "env:GEMINI_PREMIUM_MODEL",
    costClass: "paid-api",
    privacy: "external-provider",
    latency: "low",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 512,
    enabled: true,
  },
  {
    id: "bedrock-premium",
    name: "Amazon Bedrock Premium",
    provider: "bedrock",
    description: "AWS-managed provider for a cloud-native enterprise LLM architecture story.",
    tier: "premium",
    modelId: "env:BEDROCK_MODEL_ID",
    costClass: "aws-managed",
    privacy: "aws-managed",
    latency: "variable",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 512,
    enabled: true,
  },
  {
    id: "vllm-qwen-7b",
    name: "Self-hosted vLLM Qwen 7B",
    provider: "vllm",
    description: "Future self-hosted open-source 7B model served through vLLM on EKS GPU nodes.",
    tier: "premium",
    modelId: "Qwen/Qwen2.5-7B-Instruct",
    costClass: "self-hosted",
    privacy: "internal",
    latency: "medium",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 512,
    enabled: true,
  },
  {
    id: "ollama-local",
    name: "Ollama Local",
    provider: "ollama",
    description: "Local open-source model provider for low-cost development and testing.",
    tier: "premium",
    modelId: "llama3.1",
    costClass: "free-local",
    privacy: "internal",
    latency: "medium",
    defaultTemperature: 0.2,
    defaultMaxNewTokens: 512,
    enabled: true,
  },
];

export function getProvidersForMode(mode: "basic" | "premium" | "compare") {
  if (mode === "basic") {
    return providerCatalog.filter((provider) => provider.id === "finance-eks");
  }

  if (mode === "premium") {
    return providerCatalog.filter((provider) => provider.tier === "premium");
  }

  return providerCatalog;
}

export const comparisonPairs = [
  {
    left: "finance-adapter",
    right: "openai-4_1",
    label: "Adapter vs GPT-4.1",
  },
  {
    left: "finance-adapter",
    right: "claude-sonnet",
    label: "Adapter vs Claude Sonnet",
  },
  {
    left: "finance-base",
    right: "finance-adapter",
    label: "Base vs Adapter",
  },
];

export function getProviderById(providerId: string): ProviderOption {
  const provider = providerCatalog.find((item) => item.id === providerId);

  if (!provider) {
    return providerCatalog[0];
  }

  return provider;
}

export function getProvidersByTier(tier: ProviderOption["tier"]) {
  if (tier === "basic") {
    return providerCatalog.filter((provider) => provider.tier === "basic");
  }

  return providerCatalog.filter(
    (provider) => provider.tier === "premium" || provider.id === "finance-adapter",
  );
}