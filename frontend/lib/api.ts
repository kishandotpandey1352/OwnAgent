import type {
  ChatRequestInput,
  ComparisonRequestInput,
  ComparisonResult,
  FinanceResponse,
  UsageMetadata,
} from "@/types";

const USE_MOCK_BACKEND =
  (process.env.NEXT_PUBLIC_USE_MOCK_BACKEND ?? "true").toLowerCase() === "true";

/**
 * Phase 3H-F-D
 *
 * These fields are intentionally kept as a local extension so the
 * web-fallback UI can be integrated without forcing an immediate rewrite
 * of every existing request type in the frontend.
 */
export type WebAwareChatRequestInput = ChatRequestInput & {
  allowWebFallback?: boolean;
  trustedWebDomains?: string[];

  /**
   * Optional Phase 3 agent fields for document-aware callers.
   * ChatPanel does not currently provide document IDs, but other pages can.
   */
  useDocuments?: boolean;
  documentIds?: string[];
  topK?: number;
};

export type WebAwareFinanceResponse = FinanceResponse & {
  web_fallback_used?: boolean;
  web_fallback_available?: boolean;
  web_fallback_reason?: string | null;
  web_research?: PublicWebResearchSummary | null;
};

export type WebPublicCitation = {
  source_number: number;
  title: string;
  url: string;
  domain: string;
  snippet?: string | null;
  page_number?: number | null;
  trust_tier?: string | null;
  content_type?: string | null;
  retrieved_at?: string | null;
};

export type WebPublicFinancialFact = {
  source_number: number;
  metric_label: string;
  canonical_metric_key?: string | null;
  raw_value?: string | null;
  numeric_value?: number | string | null;
  normalized_numeric_value?: number | string | null;
  currency?: string | null;
  scale?: string | null;
  unit_label?: string | null;
  period_label?: string | null;
  validation_score?: number | null;
};

export type PublicWebResearchSummary = {
  used?: boolean;
  available?: boolean;
  reason?: string | null;

  searched?: boolean;
  evidence_ready?: boolean;
  citation_ready?: boolean;
  structured_fact_ready?: boolean;

  citation_count?: number;
  validated_fact_count?: number;

  citations?: WebPublicCitation[];
  validated_facts?: WebPublicFinancialFact[];
  warnings?: string[];
};

type InferenceResponse = {
  ok?: boolean;

  id?: string;

  provider?: string;
  providerId?: string;

  model?: string;
  model_id?: string;

  /**
   * Legacy inference routes return output.
   * The LangGraph /agents/analyze route returns answer.
   */
  output?: string;
  answer?: string;

  latency_ms?: number;

  source?:
    | "premium"
    | "basic"
    | "live"
    | "mock";

  request_id?: string;
  requestId?: string;

  fallback_used?: boolean;
  fallback_from?: string;

  /**
   * Phase 3H public web-fallback fields.
   * Depending on the backend response version, the flags may be present
   * at the top level and/or inside web_research.
   */
  web_fallback_used?: boolean;
  web_fallback_available?: boolean;
  web_fallback_reason?: string | null;
  web_research?: PublicWebResearchSummary | null;

  error?: string;
  detail?: string;

  usage?: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
};

function now() {
  return typeof performance !== "undefined"
    ? performance.now()
    : Date.now();
}

function toTokenCount(text: string) {
  return Math.max(
    1,
    Math.round(
      text
        .trim()
        .split(/\s+/)
        .filter(Boolean).length * 1.2,
    ),
  );
}

function getTaskEndpoint(
  task: ChatRequestInput["task"],
) {
  if (task === "summarize") {
    return "/api/backend/summarize";
  }

  if (task === "qa") {
    return "/api/backend/qa";
  }

  return "/api/backend/risk-analysis";
}

function getPremiumProviderId(
  provider: ChatRequestInput["provider"],
) {
  if (provider.provider === "finance-eks") {
    return "finance-eks";
  }

  return provider.id;
}

function shouldUsePremiumRoute(
  input: ChatRequestInput,
) {
  if (input.mode === "premium") {
    return true;
  }

  if (input.mode === "compare") {
    return input.provider.tier === "premium";
  }

  return false;
}

/**
 * A request uses the LangGraph agent route when it contains Phase 3
 * agent/web-fallback fields.
 *
 * ChatPanel now sends allowWebFallback and trustedWebDomains explicitly,
 * so ChatPanel requests go through /api/agents/analyze.
 *
 * Existing comparison requests do not provide these fields and therefore
 * continue using the existing basic/premium inference routes.
 */
function shouldUseAgentRoute(
  input: WebAwareChatRequestInput,
) {
  return (
    input.allowWebFallback !== undefined
    || input.trustedWebDomains !== undefined
    || input.useDocuments !== undefined
    || input.documentIds !== undefined
    || input.topK !== undefined
  );
}

function buildBasicRequestBody(
  input: ChatRequestInput,
) {
  const maxNewTokens =
    input.maxNewTokens
    ?? input.provider.defaultMaxNewTokens;

  const temperature =
    input.temperature
    ?? input.provider.defaultTemperature;

  const context =
    input.context?.trim();

  if (input.task === "summarize") {
    return {
      text: context
        ? `${input.prompt}\n\nInstructions:\n${context}`
        : input.prompt,

      max_new_tokens:
        maxNewTokens,

      temperature,
    };
  }

  if (input.task === "qa") {
    return {
      question:
        input.prompt,

      context:
        context ?? "",

      max_new_tokens:
        maxNewTokens,

      temperature,
    };
  }

  return {
    text: context
      ? `${input.prompt}\n\nRisk focus:\n${context}`
      : input.prompt,

    max_new_tokens:
      maxNewTokens,

    temperature,
  };
}

function buildPremiumRequestBody(
  input: ChatRequestInput,
) {
  return {
    providerId:
      getPremiumProviderId(
        input.provider,
      ),

    mode:
      input.mode === "compare"
        ? "compare"
        : "premium",

    task:
      input.task,

    prompt:
      input.prompt,

    context:
      input.context ?? "",

    temperature:
      input.temperature
      ?? input.provider.defaultTemperature,

    maxNewTokens:
      input.maxNewTokens
      ?? input.provider.defaultMaxNewTokens,
  };
}

/**
 * Build the public request sent to the Next.js
 * /api/agents/analyze proxy.
 *
 * IMPORTANT:
 * - allow_web_fallback is permission only.
 * - The backend still performs local tools and deterministic gap detection
 *   before deciding whether web research is necessary.
 * - trusted_web_domains is a preference/allow-list hint; backend guards
 *   still enforce their own limits.
 *
 * The existing ChatPanel "context" is legacy one-shot context. It is kept
 * in metadata so it is not accidentally turned into a huge web-search
 * query. Proper document-aware agent calls should use documentIds.
 */
function buildAgentRequestBody(
  input: WebAwareChatRequestInput,
) {
  const trustedWebDomains =
    Array.isArray(
      input.trustedWebDomains,
    )
      ? input.trustedWebDomains
          .filter(
            (
              value,
            ): value is string =>
              typeof value === "string",
          )
          .map(
            (value) =>
              value.trim(),
          )
          .filter(Boolean)
      : [];

  const documentIds =
    Array.isArray(
      input.documentIds,
    )
      ? input.documentIds
          .filter(
            (
              value,
            ): value is string =>
              typeof value === "string",
          )
          .map(
            (value) =>
              value.trim(),
          )
          .filter(Boolean)
      : [];

  const useDocuments =
    input.useDocuments
    ?? documentIds.length > 0;

  return {
    question:
      input.prompt.trim(),

    provider_id:
      getPremiumProviderId(
        input.provider,
      ),

    use_documents:
      useDocuments,

    document_ids:
      documentIds,

    top_k:
      input.topK ?? 8,

    allow_web_fallback:
      input.allowWebFallback
      ?? false,

    trusted_web_domains:
      trustedWebDomains,

    metadata: {
      frontend_task:
        input.task,

      frontend_mode:
        input.mode,

      /**
       * Kept for traceability/backward compatibility.
       * This is NOT a replacement for document_ids in the Phase 3
       * document-RAG workflow.
       */
      context:
        input.context ?? "",

      temperature:
        input.temperature
        ?? input.provider.defaultTemperature,

      max_new_tokens:
        input.maxNewTokens
        ?? input.provider.defaultMaxNewTokens,
    },
  };
}

function buildUsage(
  params: {
    provider: string;
    modelId: string;
    task: UsageMetadata["task"];

    prompt: string;
    output: string;

    latencyMs: number;

    source:
      UsageMetadata["source"];

    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
  },
): UsageMetadata {
  const estimatedPromptTokens =
    toTokenCount(
      params.prompt,
    );

  const estimatedCompletionTokens =
    toTokenCount(
      params.output,
    );

  const promptTokens =
    params.promptTokens
    ?? estimatedPromptTokens;

  const completionTokens =
    params.completionTokens
    ?? estimatedCompletionTokens;

  const totalTokens =
    params.totalTokens
    ?? Math.max(
      1,
      promptTokens
      + completionTokens,
    );

  return {
    provider:
      params.provider,

    modelId:
      params.modelId,

    task:
      params.task,

    promptTokens,

    completionTokens,

    totalTokens,

    latencyMs:
      Math.max(
        1,
        Math.round(
          params.latencyMs,
        ),
      ),

    source:
      params.source,
  };
}

function titleFromPrompt(
  prompt: string,
  prefix: string,
) {
  const cleaned =
    prompt
      .replace(
        /\s+/g,
        " ",
      )
      .trim();

  const snippet =
    cleaned.slice(
      0,
      64,
    );

  if (
    cleaned.length <= 64
  ) {
    return `${prefix}: ${snippet}`;
  }

  return `${prefix}: ${snippet}...`;
}

function titleFromTask(
  input: ChatRequestInput,
) {
  if (
    input.task === "summarize"
  ) {
    return titleFromPrompt(
      input.prompt,
      "Finance Summary",
    );
  }

  if (
    input.task === "qa"
  ) {
    return titleFromPrompt(
      input.prompt,
      "Finance Q&A",
    );
  }

  return titleFromPrompt(
    input.prompt,
    "Risk Analysis",
  );
}

function mockOutput(
  input: ChatRequestInput,
  variant = 0,
) {
  const seeds = [
    "The filing suggests steady revenue momentum, but margin expansion depends on cost control and working-capital discipline.",
    "Cash flow remains constructive, yet leverage, refinancing cadence, and guidance credibility deserve monitoring.",
    "The risk profile centers on execution, pricing pressure, and sensitivity to macro demand in the next two quarters.",
  ];

  const base =
    seeds[
      variant
      % seeds.length
    ];

  const providerLabel =
    `${input.provider.provider} / ${input.provider.name}`;

  return (
    `${base} `
    + `This mock response was generated for ${providerLabel} `
    + `in ${input.mode} mode against the ${input.task} workflow. `
    + `Prompt focus: ${input.prompt.slice(0, 80)}`
    + (
      input.prompt.length > 80
        ? "..."
        : ""
    )
  );
}

function mockResponse(
  input: ChatRequestInput,
  variant = 0,
): FinanceResponse {
  const started =
    now();

  const output =
    mockOutput(
      input,
      variant,
    );

  const latencyMs =
    Math.round(
      180
      + variant * 35
      + input.prompt.length * 1.3,
    );

  return {
    id:
      `mock-${Date.now()}-${variant}`,

    prompt:
      input.prompt,

    title:
      titleFromTask(
        input,
      ),

    output,

    provider:
      input.provider.provider,

    modelId:
      input.provider.modelId,

    task:
      input.task,

    mode:
      input.mode,

    web_fallback_available:
      false,

    web_fallback_used:
      false,

    createdAt:
      new Date().toISOString(),

    usage:
      buildUsage({
        provider:
          input.provider.provider,

        modelId:
          input.provider.modelId,

        task:
          input.task,

        prompt:
          input.prompt,

        output,

        latencyMs:
          latencyMs
          + Math.max(
            0,
            now() - started,
          ),

        source:
          "mock",
      }),
  };
}

function failedComparisonResponse(
  input: ChatRequestInput,
  error: unknown,
): FinanceResponse {
  const message =
    error instanceof Error
      ? error.message
      : "Provider request failed";

  return {
    id:
      `error-${Date.now()}-${input.provider.id}`,

    prompt:
      input.prompt,

    title:
      `${input.provider.name} failed`,

    output:
      `Provider unavailable: ${message}`,

    provider:
      input.provider.provider,

    modelId:
      input.provider.modelId,

    task:
      input.task,

    mode:
      input.mode,

    web_fallback_available:
      false,

    web_fallback_used:
      false,

    createdAt:
      new Date().toISOString(),

    usage:
      buildUsage({
        provider:
          input.provider.provider,

        modelId:
          input.provider.modelId,

        task:
          input.task,

        prompt:
          input.prompt,

        output:
          message,

        latencyMs:
          1,

        source:
          "live",

        promptTokens:
          0,

        completionTokens:
          0,

        totalTokens:
          0,
      }),
  };
}

function readErrorMessage(
  text: string,
  status: number,
) {
  const fallback =
    text
    || `Request failed with status ${status}`;

  if (!text) {
    return fallback;
  }

  try {
    const payload =
      JSON.parse(
        text,
      ) as {
        error?: unknown;
        detail?: unknown;
      };

    if (
      typeof payload.error === "string"
      && payload.error.trim()
    ) {
      return payload.error;
    }

    if (
      typeof payload.detail === "string"
      && payload.detail.trim()
    ) {
      return payload.detail;
    }
  }
  catch {
    // The body was not JSON. Use the raw response text.
  }

  return fallback;
}

async function postInference(
  input: WebAwareChatRequestInput,
): Promise<InferenceResponse> {
  const controller =
    new AbortController();

  const timeoutId =
    window.setTimeout(
      () =>
        controller.abort(),
      10 * 60 * 1000,
    );

  const startedAt =
    now();

  const useAgentRoute =
    shouldUseAgentRoute(
      input,
    );

  const isPremium =
    shouldUsePremiumRoute(
      input,
    );

  const endpoint =
    useAgentRoute
      ? "/api/agents/analyze"
      : isPremium
        ? "/api/premium/inference"
        : getTaskEndpoint(
            input.task,
          );

  const body =
    useAgentRoute
      ? buildAgentRequestBody(
          input,
        )
      : isPremium
        ? buildPremiumRequestBody(
            input,
          )
        : buildBasicRequestBody(
            input,
          );

  try {
    const response =
      await fetch(
        endpoint,
        {
          method:
            "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body:
            JSON.stringify(
              body,
            ),

          signal:
            controller.signal,

          cache:
            "no-store",
        },
      );

    const text =
      await response.text();

    if (
      !response.ok
    ) {
      throw new Error(
        readErrorMessage(
          text,
          response.status,
        ),
      );
    }

    if (!text.trim()) {
      throw new Error(
        "The server returned an empty response.",
      );
    }

    const payload =
      JSON.parse(
        text,
      ) as InferenceResponse;

    return {
      ...payload,

      latency_ms:
        payload.latency_ms
        ?? Math.max(
          1,
          Math.round(
            now()
            - startedAt,
          ),
        ),
    };
  }
  finally {
    window.clearTimeout(
      timeoutId,
    );
  }
}

function resolveWebFallbackState(
  payload: InferenceResponse,
) {
  const summary =
    payload.web_research;

  const used =
    payload.web_fallback_used
    ?? summary?.used
    ?? false;

  const available =
    payload.web_fallback_available
    ?? summary?.available
    ?? false;

  const reason =
    payload.web_fallback_reason
    ?? summary?.reason
    ?? null;

  return {
    used,
    available,
    reason,
  };
}

export async function sendFinancePrompt(
  input: WebAwareChatRequestInput,
): Promise<WebAwareFinanceResponse> {
  if (
    USE_MOCK_BACKEND
  ) {
    return mockResponse(
      input,
    );
  }

  const startedAt =
    now();

  const payload =
    await postInference(
      input,
    );

  const createdAt =
    new Date().toISOString();

  const fallbackNote =
    payload.fallback_used
    && payload.fallback_from
      ? (
        "\n\nFallback used: "
        + `${payload.fallback_from} -> `
        + `${payload.providerId ?? payload.provider ?? "unknown provider"}`
      )
      : "";

  const output =
    `${payload.answer ?? payload.output ?? ""}${fallbackNote}`;

  const provider =
    payload.provider
    ?? input.provider.provider;

  const modelId =
    payload.model
    ?? payload.model_id
    ?? input.provider.modelId;

  const latencyMs =
    payload.latency_ms
    ?? Math.max(
      1,
      Math.round(
        now()
        - startedAt,
      ),
    );

  const webFallback =
    resolveWebFallbackState(
      payload,
    );

  return {
    id:
      payload.id
      ?? payload.request_id
      ?? payload.requestId
      ?? `response-${Date.now()}`,

    prompt:
      input.prompt,

    title:
      titleFromTask(
        input,
      ),

    output,

    provider,

    modelId,

    task:
      input.task,

    mode:
      input.mode,

    createdAt,

    web_fallback_used:
      webFallback.used,

    web_fallback_available:
      webFallback.available,

    web_fallback_reason:
      webFallback.reason,

    web_research:
      payload.web_research
      ?? null,

    usage:
      buildUsage({
        provider,

        modelId,

        task:
          input.task,

        prompt:
          input.prompt,

        output,

        latencyMs,

        source:
          "live",

        promptTokens:
          payload.usage
            ?.prompt_tokens,

        completionTokens:
          payload.usage
            ?.completion_tokens,

        totalTokens:
          payload.usage
            ?.total_tokens,
      }),
  };
}

export async function runComparison(
  input: ComparisonRequestInput,
): Promise<ComparisonResult> {
  if (
    USE_MOCK_BACKEND
  ) {
    const left =
      mockResponse(
        {
          task:
            input.task,

          prompt:
            input.prompt,

          context:
            input.context,

          provider:
            input.leftProvider,

          mode:
            "compare",

          accessToken:
            input.accessToken,

          temperature:
            input.leftProvider
              .defaultTemperature,

          maxNewTokens:
            input.leftProvider
              .defaultMaxNewTokens,
        },
        0,
      );

    const right =
      mockResponse(
        {
          task:
            input.task,

          prompt:
            input.prompt,

          context:
            input.context,

          provider:
            input.rightProvider,

          mode:
            "compare",

          accessToken:
            input.accessToken,

          temperature:
            input.rightProvider
              .defaultTemperature
            + 0.05,

          maxNewTokens:
            input.rightProvider
              .defaultMaxNewTokens,
        },
        1,
      );

    return {
      left,
      right,
    };
  }

  const leftInput:
    ChatRequestInput = {
      task:
        input.task,

      prompt:
        input.prompt,

      context:
        input.context,

      provider:
        input.leftProvider,

      mode:
        "compare",

      accessToken:
        input.accessToken,

      temperature:
        input.leftProvider
          .defaultTemperature,

      maxNewTokens:
        input.leftProvider
          .defaultMaxNewTokens,
    };

  const rightInput:
    ChatRequestInput = {
      task:
        input.task,

      prompt:
        input.prompt,

      context:
        input.context,

      provider:
        input.rightProvider,

      mode:
        "compare",

      accessToken:
        input.accessToken,

      temperature:
        input.rightProvider
          .defaultTemperature
        + 0.05,

      maxNewTokens:
        input.rightProvider
          .defaultMaxNewTokens,
    };

  const [
    leftResult,
    rightResult,
  ] =
    await Promise.allSettled(
      [
        sendFinancePrompt(
          leftInput,
        ),

        sendFinancePrompt(
          rightInput,
        ),
      ],
    );

  const left =
    leftResult.status
    === "fulfilled"
      ? leftResult.value
      : failedComparisonResponse(
          leftInput,
          leftResult.reason,
        );

  const right =
    rightResult.status
    === "fulfilled"
      ? rightResult.value
      : failedComparisonResponse(
          rightInput,
          rightResult.reason,
        );

  return {
    left,
    right,
  };
}
