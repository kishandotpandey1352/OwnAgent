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
from app.models.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


def make_request(
    *,
    model: str | None = "local-model-id",
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
        temperature=0.3,
        max_output_tokens=100,
    )


def test_provider_satisfies_model_provider_protocol():
    provider = OpenAICompatibleProvider(
        provider_id="compatible-test",
        base_url="http://localhost:1234/v1",
        default_model="local-model-id",
    )

    assert isinstance(
        provider,
        ModelProvider,
    )


def test_descriptor_is_local_and_streaming():
    provider = OpenAICompatibleProvider(
        provider_id="compatible-test",
        base_url="http://localhost:1234/v1",
        default_model="local-model-id",
        location=ProviderLocation.local,
    )

    descriptor = provider.descriptor

    assert (
        descriptor.provider_id
        == "compatible-test"
    )

    assert (
        descriptor.location
        == ProviderLocation.local
    )

    assert (
        descriptor.default_model
        == "local-model-id"
    )

    assert descriptor.supports_streaming is True


def test_custom_base_url_and_model_are_used():
    captured = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured["path"] = (
            request.url.path
        )

        captured["payload"] = json.loads(
            request.content.decode()
        )

        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "model": "my-lm-studio-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content":
                                "Hello from LM Studio",
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 4,
                    "total_tokens": 14,
                },
            },
        )

    provider = OpenAICompatibleProvider(
        provider_id="lmstudio-test",
        base_url="http://localhost:1234/v1",
        transport=httpx.MockTransport(
            handler
        ),
    )

    response = provider.generate(
        ModelRequest(
            messages=[
                ModelMessage(
                    role=ModelMessageRole.user,
                    content="Hello",
                )
            ],
            model="my-lm-studio-model",
        )
    )

    assert (
        captured["path"]
        == "/v1/chat/completions"
    )

    assert (
        captured["payload"]["model"]
        == "my-lm-studio-model"
    )

    assert (
        captured["payload"]["stream"]
        is False
    )

    assert (
        response.text
        == "Hello from LM Studio"
    )

    assert (
        response.provider_id
        == "lmstudio-test"
    )

    assert (
        response.model
        == "my-lm-studio-model"
    )

    assert (
        response.usage.input_tokens
        == 10
    )

    assert (
        response.usage.output_tokens
        == 4
    )

    assert (
        response.usage.total_tokens
        == 14
    )


def test_optional_bearer_token_is_sent():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers.get(
                "authorization"
            )
            == "Bearer local-test-key"
        )

        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "OK",
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    provider = OpenAICompatibleProvider(
        provider_id="compatible-test",
        base_url="http://localhost:1234/v1",
        api_key="local-test-key",
        transport=httpx.MockTransport(
            handler
        ),
    )

    response = provider.generate(
        make_request(
            model="test-model"
        )
    )

    assert response.text == "OK"


def test_stream_normalises_sse_chunks():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        body = (
            'data: {"model":"test-model",'
            '"choices":[{"delta":{"content":"Hello "},'
            '"finish_reason":null}]}\n\n'
            'data: {"model":"test-model",'
            '"choices":[{"delta":{"content":"world"},'
            '"finish_reason":null}]}\n\n'
            'data: {"model":"test-model",'
            '"choices":[{"delta":{},'
            '"finish_reason":"stop"}]}\n\n'
            'data: [DONE]\n\n'
        )

        return httpx.Response(
            200,
            content=body.encode(),
            headers={
                "content-type":
                    "text/event-stream"
            },
        )

    provider = OpenAICompatibleProvider(
        provider_id="compatible-test",
        base_url="http://localhost:1234/v1",
        transport=httpx.MockTransport(
            handler
        ),
    )

    chunks = list(
        provider.stream(
            make_request(
                model="test-model"
            )
        )
    )

    assert (
        "".join(
            chunk.delta
            for chunk in chunks
        )
        == "Hello world"
    )

    assert (
        chunks[-1].finish_reason
        == "stop"
    )

    assert all(
        chunk.provider_id
        == "compatible-test"
        for chunk in chunks
    )


def test_health_uses_models_endpoint():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.url.path
            == "/v1/models"
        )

        return httpx.Response(
            200,
            json={
                "object": "list",
                "data": [
                    {
                        "id": "model-one",
                        "object": "model",
                    },
                    {
                        "id": "model-two",
                        "object": "model",
                    },
                ],
            },
        )

    provider = OpenAICompatibleProvider(
        provider_id="lmstudio-test",
        base_url="http://localhost:1234/v1",
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
        == 2
    )


def test_health_reports_unavailable():
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "connection refused",
            request=request,
        )

    provider = OpenAICompatibleProvider(
        provider_id="lmstudio-test",
        base_url="http://localhost:1234/v1",
        transport=httpx.MockTransport(
            handler
        ),
    )

    health = provider.health()

    assert (
        health.status
        == ModelHealthStatus.unavailable
    )


def test_local_provider_has_zero_provider_fee():
    provider = OpenAICompatibleProvider(
        provider_id="lmstudio-test",
        base_url="http://localhost:1234/v1",
        default_model="test-model",
        location=ProviderLocation.local,
    )

    estimate = provider.estimate(
        make_request(
            model=None
        )
    )

    assert estimate.local is True

    assert (
        estimate.estimated_provider_cost
        == Decimal("0")
    )

    assert estimate.pricing_available is True

    assert (
        "LOCAL_PROVIDER_NO_PROVIDER_FEE"
        in estimate.reason_codes
    )


def test_remote_compatible_provider_does_not_invent_price():
    provider = OpenAICompatibleProvider(
        provider_id="remote-compatible",
        base_url="https://example.com/v1",
        default_model="remote-model",
        location=ProviderLocation.remote,
    )

    estimate = provider.estimate(
        make_request(
            model=None
        )
    )

    assert estimate.local is False

    assert (
        estimate.estimated_provider_cost
        is None
    )

    assert estimate.pricing_available is False


def test_provider_requires_model():
    provider = OpenAICompatibleProvider(
        provider_id="compatible-test",
        base_url="http://localhost:1234/v1",
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


def test_json_mode_is_not_over_advertised():
    provider = OpenAICompatibleProvider(
        provider_id="compatible-test",
        base_url="http://localhost:1234/v1",
        default_model="test-model",
    )

    request = ModelRequest(
        messages=[
            ModelMessage(
                role=ModelMessageRole.user,
                content="Hello",
            )
        ],
        response_format="json",
    )

    with pytest.raises(
        ModelProviderContractError
    ):
        provider.generate(
            request
        )

def test_runtime_registers_lmstudio_provider():
    from app.models.runtime import (
        LMSTUDIO_LOCAL_PROVIDER_ID,
        get_model_gateway,
    )

    get_model_gateway.cache_clear()

    try:
        gateway = get_model_gateway()

        assert gateway.has_provider(
            LMSTUDIO_LOCAL_PROVIDER_ID
        )

    finally:
        get_model_gateway.cache_clear()