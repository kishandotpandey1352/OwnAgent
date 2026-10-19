from app.models.contracts import (
    ModelMessage,
    ModelMessageRole,
    ModelRequest,
    ProviderLocation,
)
from app.models.providers.openai import (
    OpenAIChatProvider,
)

from app.models.contracts import (
    ModelHealthStatus,
)

def test_openai_provider_descriptor():
    provider = OpenAIChatProvider(
        provider_id="openai-test",
        api_key="test-key",
        default_model="test-model",
    )

    descriptor = provider.descriptor

    assert descriptor.provider_id == "openai-test"
    assert (
        descriptor.location
        == ProviderLocation.remote
    )
    assert descriptor.default_model == "test-model"


def test_openai_provider_converts_system_message():
    provider = OpenAIChatProvider(
        provider_id="openai-test",
        api_key="test-key",
        default_model="test-model",
    )

    message = ModelMessage(
        role=ModelMessageRole.system,
        content="System instruction",
    )

    converted = provider._convert_message(
        message
    )

    assert converted.content == "System instruction"


def test_openai_provider_converts_user_message():
    provider = OpenAIChatProvider(
        provider_id="openai-test",
        api_key="test-key",
        default_model="test-model",
    )

    message = ModelMessage(
        role=ModelMessageRole.user,
        content="Hello",
    )

    converted = provider._convert_message(
        message
    )

    assert converted.content == "Hello"


def test_model_request_stays_provider_agnostic():
    request = ModelRequest(
        messages=[
            ModelMessage(
                role=ModelMessageRole.user,
                content="Hello",
            )
        ],
    )

    dumped = request.model_dump()

    assert "api_key" not in dumped
    assert "base_url" not in dumped
    assert "openai" not in str(
        dumped
    ).lower()

def test_openai_provider_reports_unavailable_without_key():
    provider = OpenAIChatProvider(
        provider_id="openai-test",
        api_key="",
        default_model="test-model",
    )

    health = provider.health()

    assert (
        health.status
        == ModelHealthStatus.unavailable
    )


def test_openai_provider_capabilities_are_normalized():
    provider = OpenAIChatProvider(
        provider_id="openai-test",
        api_key="test-key",
        default_model="test-model",
    )

    capabilities = provider.capabilities()

    assert capabilities.provider_id == "openai-test"
    assert capabilities.text_generation is True
    assert capabilities.streaming is True
    assert capabilities.location == ProviderLocation.remote


def test_openai_provider_estimate_does_not_invent_pricing():
    provider = OpenAIChatProvider(
        provider_id="openai-test",
        api_key="test-key",
        default_model="test-model",
    )

    estimate = provider.estimate(
        ModelRequest(
            messages=[
                ModelMessage(
                    role=ModelMessageRole.user,
                    content="Hello",
                )
            ]
        )
    )

    assert estimate.local is False
    assert estimate.pricing_available is False

    assert (
        estimate.estimated_provider_cost
        is None
    )

    assert (
        "PRICING_METADATA_UNAVAILABLE"
        in estimate.reason_codes
    )