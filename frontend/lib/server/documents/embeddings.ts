type OpenAIEmbeddingResponse = {
  data?: Array<{
    embedding?: number[];
    index?: number;
  }>;
  usage?: {
    prompt_tokens?: number;
    total_tokens?: number;
  };
  error?: {
    message?: string;
  };
};

export function getEmbeddingModel() {
  return process.env.DOCUMENT_EMBEDDING_MODEL ?? "text-embedding-3-small";
}

export async function createEmbedding(input: string) {
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    throw new Error("OPENAI_API_KEY is required for Phase 2A embeddings.");
  }

  if (!input.trim()) {
    throw new Error("Cannot create embedding for empty text.");
  }

  const model = getEmbeddingModel();

  const response = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      input,
      encoding_format: "float",
    }),
    cache: "no-store",
  });

  const payload = (await response.json()) as OpenAIEmbeddingResponse;

  if (!response.ok) {
    throw new Error(
      payload.error?.message ??
        `OpenAI embedding request failed with status ${response.status}`,
    );
  }

  const embedding = payload.data?.[0]?.embedding;

  if (!embedding?.length) {
    throw new Error("OpenAI embedding response did not include an embedding.");
  }

  return {
    embedding,
    model,
    usage: payload.usage,
  };
}

export async function createEmbeddings(inputs: string[]) {
  const apiKey = process.env.OPENAI_API_KEY;

  if (!apiKey) {
    throw new Error("OPENAI_API_KEY is required for Phase 2A embeddings.");
  }

  const cleanInputs = inputs.map((item) => item.trim()).filter(Boolean);

  if (!cleanInputs.length) {
    return {
      embeddings: [],
      model: getEmbeddingModel(),
      usage: undefined,
    };
  }

  const model = getEmbeddingModel();

  const response = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model,
      input: cleanInputs,
      encoding_format: "float",
    }),
    cache: "no-store",
  });

  const payload = (await response.json()) as OpenAIEmbeddingResponse;

  if (!response.ok) {
    throw new Error(
      payload.error?.message ??
        `OpenAI embedding request failed with status ${response.status}`,
    );
  }

  const embeddings =
    payload.data
      ?.sort((left, right) => (left.index ?? 0) - (right.index ?? 0))
      .map((item) => item.embedding)
      .filter((embedding): embedding is number[] => Boolean(embedding)) ?? [];

  if (embeddings.length !== cleanInputs.length) {
    throw new Error("Embedding count did not match input count.");
  }

  return {
    embeddings,
    model,
    usage: payload.usage,
  };
}