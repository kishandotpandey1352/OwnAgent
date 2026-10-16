export type AppMode = "basic" | "premium" | "compare";
export type FinanceTask = "summarize" | "qa" | "risk-analysis";
export type RequestSource = "live" | "mock";

export interface AuthState {
  accessToken: string;
  displayName: string;
  remember: boolean;
  issuedAt: string;
}

export interface ProviderOption {
  id: string;
  name: string;
  provider:
    | "finance-eks"
    | "openai"
    | "anthropic"
    | "gemini"
    | "bedrock"
    | "vllm"
    | "ollama";
  description: string;
  tier: Exclude<AppMode, "compare">;
  modelId: string;
  costClass: "self-hosted" | "paid-api" | "free-local" | "aws-managed";
  privacy: "internal" | "external-provider" | "aws-managed";
  latency: "low" | "medium" | "high" | "variable";
  defaultTemperature: number;
  defaultMaxNewTokens: number;
  enabled: boolean;
}

export interface UsageMetadata {
  provider: string;
  modelId: string;
  task: FinanceTask;
  totalTokens: number;
  promptTokens: number;
  completionTokens: number;
  latencyMs: number;
  source: RequestSource;
}

export interface FinanceResponse {
  web_fallback_available: boolean;
  web_fallback_used: any;
  id: string;
  prompt: string;
  title: string;
  output: string;
  provider: string;
  modelId: string;
  task: FinanceTask;
  mode: AppMode;
  createdAt: string;
  usage: UsageMetadata;
}

export interface ComparisonResult {
  left: FinanceResponse;
  right: FinanceResponse;
}

export type AttachmentKind =
  | "pdf"
  | "docx"
  | "text"
  | "csv"
  | "image"
  | "unknown";

export interface HistoryAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  kind: AttachmentKind;
  pageCount?: number;
  truncated?: boolean;
  extractedChars?: number;
}

export interface HistoryEntry extends FinanceResponse {
  sourcePrompt: string;
  context?: string;
  attachments?: HistoryAttachment[];
}

export interface ChatRequestInput {
  task: FinanceTask;
  prompt: string;
  context?: string;
  provider: ProviderOption;
  mode: AppMode;
  accessToken?: string;
  temperature?: number;
  maxNewTokens?: number;
}

export interface ComparisonRequestInput {
  prompt: string;
  context?: string;
  leftProvider: ProviderOption;
  rightProvider: ProviderOption;
  task: FinanceTask;
  accessToken?: string;
}


