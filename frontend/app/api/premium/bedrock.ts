import {
  BedrockRuntimeClient,
  ConverseCommand,
} from "@aws-sdk/client-bedrock-runtime";

import { buildTaskPrompt } from "./prompt";
import type { PremiumInferenceInput, PremiumInferenceOutput } from "./types";

type BedrockUsage = {
  inputTokens?: number;
  outputTokens?: number;
  totalTokens?: number;
};

function getBedrockClient() {
  return new BedrockRuntimeClient({
    region: process.env.AWS_REGION ?? "us-east-1",
  });
}

function getBedrockModelId() {
  return (
    process.env.BEDROCK_MODEL_ID ??
    "anthropic.claude-3-5-haiku-20241022-v1:0"
  );
}

function extractTextFromBedrockResponse(output: unknown) {
  const response = output as {
    output?: {
      message?: {
        content?: Array<{
          text?: string;
        }>;
      };
    };
  };

  return (
    response.output?.message?.content
      ?.map((part) => part.text ?? "")
      .filter(Boolean)
      .join("\n")
      .trim() ?? ""
  );
}

function extractUsage(output: unknown): BedrockUsage | undefined {
  const response = output as {
    usage?: {
      inputTokens?: number;
      outputTokens?: number;
      totalTokens?: number;
    };
  };

  return response.usage;
}

export async function callBedrock(
  input: PremiumInferenceInput,
  startedAt: number,
): Promise<PremiumInferenceOutput> {
  const client = getBedrockClient();
  const modelId = getBedrockModelId();
  const prompt = buildTaskPrompt(input);

  const maxTokens = Number(
    process.env.BEDROCK_MAX_TOKENS ?? input.maxNewTokens ?? 512,
  );

  const command = new ConverseCommand({
    modelId,
    messages: [
      {
        role: "user",
        content: [
          {
            text: prompt,
          },
        ],
      },
    ],
    inferenceConfig: {
      temperature: input.temperature ?? 0.2,
      maxTokens,
    },
  });

  const response = await client.send(command);
  const output = extractTextFromBedrockResponse(response);
  const usage = extractUsage(response);

  return {
    id: `bedrock-${Date.now()}`,
    provider: "bedrock",
    providerId: input.providerId,
    model_id: modelId,
    output,
    latency_ms: Math.max(1, Math.round(Date.now() - startedAt)),
    source: "premium",
    usage: {
      prompt_tokens: usage?.inputTokens,
      completion_tokens: usage?.outputTokens,
      total_tokens: usage?.totalTokens,
    },
  };
}