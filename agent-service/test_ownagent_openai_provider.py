from app.models.contracts import (
    ModelMessage,
    ModelMessageRole,
    ModelRequest,
    ProviderLocation,
)
from app.models.providers.openai import (
    OpenAIChatProvider,
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