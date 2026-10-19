import json
from decimal import Decimal

import httpx
import pytest

from app.models.contracts import (
    ModelHealthStatus,
    ModelMessage,
    ModelMessageRole,
    ModelRequest,
    ProviderLocation,
)
from app.models.errors import (
    ModelProviderContractError,
)
from app.models.provider import (
    ModelProvider,
)
from app.models.providers.ollama import (
    OllamaProvider,
)


def make_request(
    *,
    model: str | None = "qwen-test:latest",
    response_format: str = "text",
) -> ModelRequest:
    return ModelRequest(
        messages=[
            ModelMessage(
                role=ModelMessageRole.system,
                content="You are a test assistant.",
            ),
            ModelMessage(
                role=ModelMessageRole.user,
                content="Hello",
            ),
        ],
        model=model,
        temperature=0.2,
        max_output_tokens=100,
        response_format=response_format,
    )


def test_ollama_provider_satisfies_model_provider_protocol():
    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        default_model="qwen-test",
    )

    assert isinstance(
        provider,
        ModelProvider,
    )


def test_ollama_provider_descriptor_is_local():
    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        default_model="qwen-test",
    )

    descriptor = provider.descriptor

    assert descriptor.provider_id == "ollama-test"

    assert (
        descriptor.location
        == ProviderLocation.local
    )

    assert descriptor.supports_streaming is True
    assert descriptor.supports_json is True


def test_ollama_generate_normalises_response():
    captured_payload = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == "/api/chat"

        captured_payload.update(
            json.loads(
                request.content.decode()
            )
        )

        return httpx.Response(
            200,
            json={
                "model": "qwen-test:latest",
                "message": {
                    "role": "assistant",
                    "content": "Hello from Ollama",
                },
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 12,
                "eval_count": 4,
            },
        )

    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        transport=httpx.MockTransport(
            handler
        ),
    )

    response = provider.generate(
        make_request()
    )

    assert response.text == "Hello from Ollama"
    assert response.provider_id == "ollama-test"
    assert response.model == "qwen-test:latest"

    assert response.usage.input_tokens == 12
    assert response.usage.output_tokens == 4
    assert response.usage.total_tokens == 16

    assert captured_payload["stream"] is False
    assert captured_payload["model"] == "qwen-test:latest"

    assert (
        captured_payload["options"]["temperature"]
        == 0.2
    )

    assert (
        captured_payload["options"]["num_predict"]
        == 100
    )


def test_ollama_json_mode_is_forwarded():
    captured_payload = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured_payload.update(
            json.loads(
                request.content.decode()
            )
        )

        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": '{"ok": true}',
                },
                "done": True,
                "eval_count": 2,
                "prompt_eval_count": 5,
            },
        )

    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        transport=httpx.MockTransport(
            handler
        ),
    )

    response = provider.generate(
        make_request(
            response_format="json"
        )
    )

    assert response.text == '{"ok": true}'

    assert (
        captured_payload["format"]
        == "json"
    )


def test_ollama_stream_normalises_chunks():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        content = (
            b'{"message":{"content":"Hello "},'
            b'"done":false}\n'
            b'{"message":{"content":"world"},'
            b'"done":false}\n'
            b'{"message":{"content":""},'
            b'"done":true,"done_reason":"stop"}\n'
        )

        return httpx.Response(
            200,
            content=content,
            headers={
                "content-type":
                    "application/x-ndjson"
            },
        )

    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        transport=httpx.MockTransport(
            handler
        ),
    )

    chunks = list(
        provider.stream(
            make_request()
        )
    )

    assert (
        "".join(
            chunk.delta
            for chunk in chunks
        )
        == "Hello world"
    )

    assert chunks[-1].finish_reason == "stop"

    assert all(
        chunk.provider_id == "ollama-test"
        for chunk in chunks
    )


def test_ollama_health_reports_healthy():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == "/api/tags"

        return httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name":
                            "qwen-test:latest"
                    }
                ]
            },
        )

    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        transport=httpx.MockTransport(
            handler
        ),
    )

    health = provider.health()

    assert (
        health.status
        == ModelHealthStatus.healthy
    )

    assert (
        health.metadata["model_count"]
        == 1
    )


def test_ollama_health_reports_unavailable():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "connection refused",
            request=request,
        )

    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        transport=httpx.MockTransport(
            handler
        ),
    )

    health = provider.health()

    assert (
        health.status
        == ModelHealthStatus.unavailable
    )


def test_ollama_capabilities_are_normalised():
    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        default_model="qwen-test",
    )

    result = provider.capabilities()

    assert result.provider_id == "ollama-test"
    assert result.location == ProviderLocation.local
    assert result.text_generation is True
    assert result.streaming is True
    assert result.json_mode is True

    assert result.tools is False
    assert result.vision is False


def test_ollama_estimate_has_zero_provider_fee():
    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        default_model="qwen-test",
    )

    result = provider.estimate(
        make_request(
            model=None
        )
    )

    assert result.local is True

    assert (
        result.estimated_provider_cost
        == Decimal("0")
    )

    assert result.pricing_available is True

    assert (
        "LOCAL_PROVIDER_NO_PROVIDER_FEE"
        in result.reason_codes
    )


def test_ollama_requires_a_model():
    provider = OllamaProvider(
        provider_id="ollama-test",
        base_url="http://localhost:11434",
        default_model=None,
    )

    request = ModelRequest(
        messages=[
            ModelMessage(
                role=ModelMessageRole.user,
                content="Hello",
            )
        ]
    )

    with pytest.raises(
        ModelProviderContractError
    ):
        provider.generate(
            request
        )

def test_runtime_registers_ollama_provider():
    from app.models.runtime import (
        OLLAMA_LOCAL_PROVIDER_ID,
        get_model_gateway,
    )

    gateway = get_model_gateway()

    provider_id = (
        gateway.resolve_provider_id(
            OLLAMA_LOCAL_PROVIDER_ID
        )
    )

    assert (
        provider_id
        == OLLAMA_LOCAL_PROVIDER_ID
    )

def test_runtime_registers_ollama_provider():
    from app.models.runtime import (
        OLLAMA_LOCAL_PROVIDER_ID,
        get_model_gateway,
    )

    gateway = get_model_gateway()

    assert gateway.has_provider(
        OLLAMA_LOCAL_PROVIDER_ID
    )