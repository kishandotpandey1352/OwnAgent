import os
from typing import Any

import httpx


VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://host.docker.internal:8001")
VLLM_MODEL_NAME = os.getenv("VLLM_MODEL_NAME", "finance-qwen1.5b")


class VLLMClientError(RuntimeError):
    pass


async def generate_chat_completion(
    messages: list[dict[str, str]],
    max_tokens: int = 256,
    temperature: float = 0.2,
) -> dict[str, Any]:
    url = f"{VLLM_BASE_URL.rstrip('/')}/v1/chat/completions"

    payload = {
        "model": VLLM_MODEL_NAME,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError as exc:
        raise VLLMClientError(f"vLLM request failed: {exc}") from exc


def extract_text(response: dict[str, Any]) -> str:
    try:
        return response["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise VLLMClientError(f"Unexpected vLLM response format: {response}") from exc


def extract_usage(response: dict[str, Any]) -> dict[str, int]:
    usage = response.get("usage", {})

    return {
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
        "total_tokens": int(usage.get("total_tokens", 0)),
    }