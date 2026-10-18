import pytest

from app.models.contracts import (
    ModelMessage,
    ModelMessageRole,
    ModelProviderDescriptor,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    ProviderLocation,
)
from app.models.errors import (
    ModelProviderAlreadyRegisteredError,
    ModelProviderContractError,
    ModelProviderNotFoundError,
)
from app.models.gateway import ModelGateway
from app.models.registry import (
    ModelProviderRegistry,
)


class FakeProvider:
    def __init__(
        self,
        provider_id: str,
        *,
        location: ProviderLocation,
        response_provider_id: str | None = None,
    ) -> None:
        self._descriptor = (
            ModelProviderDescriptor(
                provider_id=provider_id,
                location=location,
                default_model="fake-model",
            )
        )

        self._response_provider_id = (
            response_provider_id
            or provider_id
        )


    @property
    def descriptor(
        self,
    ) -> ModelProviderDescriptor:
        return self._descriptor


    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        return ModelResponse(
            text="fake response",
            provider_id=(
                self._response_provider_id
            ),
            model=(
                request.model
                or self.descriptor.default_model
                or "fake-model"
            ),
            usage=ModelUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
            ),
            finish_reason="stop",
        )


def make_request() -> ModelRequest:
    return ModelRequest(
        messages=[
            ModelMessage(
                role=ModelMessageRole.user,
                content="Hello OwnAgent",
            )
        ]
    )


def test_registry_registers_provider():
    registry = ModelProviderRegistry()

    registry.register(
        FakeProvider(
            "local-test",
            location=ProviderLocation.local,
        )
    )

    assert registry.contains(
        "local-test"
    )


def test_registry_rejects_duplicate_provider():
    registry = ModelProviderRegistry()

    provider = FakeProvider(
        "local-test",
        location=ProviderLocation.local,
    )

    registry.register(provider)

    with pytest.raises(
        ModelProviderAlreadyRegisteredError
    ):
        registry.register(provider)


def test_gateway_routes_to_explicit_provider():
    registry = ModelProviderRegistry(
        [
            FakeProvider(
                "local-test",
                location=ProviderLocation.local,
            ),
            FakeProvider(
                "cloud-test",
                location=ProviderLocation.remote,
            ),
        ]
    )

    gateway = ModelGateway(
        registry=registry,
    )

    response = gateway.generate(
        request=make_request(),
        provider_id="local-test",
    )

    assert response.provider_id == "local-test"
    assert response.text == "fake response"


def test_gateway_uses_default_provider():
    registry = ModelProviderRegistry(
        [
            FakeProvider(
                "local-test",
                location=ProviderLocation.local,
            )
        ]
    )

    gateway = ModelGateway(
        registry=registry,
        default_provider_id="local-test",
    )

    response = gateway.generate(
        request=make_request(),
    )

    assert response.provider_id == "local-test"


def test_gateway_rejects_unknown_provider():
    registry = ModelProviderRegistry()

    gateway = ModelGateway(
        registry=registry,
    )

    with pytest.raises(
        ModelProviderNotFoundError
    ):
        gateway.generate(
            request=make_request(),
            provider_id="does-not-exist",
        )


def test_gateway_rejects_provider_identity_mismatch():
    registry = ModelProviderRegistry(
        [
            FakeProvider(
                "expected-provider",
                location=ProviderLocation.remote,
                response_provider_id="wrong-provider",
            )
        ]
    )

    gateway = ModelGateway(
        registry=registry,
    )

    with pytest.raises(
        ModelProviderContractError
    ):
        gateway.generate(
            request=make_request(),
            provider_id="expected-provider",
        )


def test_provider_location_is_explicit():
    registry = ModelProviderRegistry(
        [
            FakeProvider(
                "local-test",
                location=ProviderLocation.local,
            )
        ]
    )

    descriptor = (
        registry
        .get("local-test")
        .descriptor
    )

    assert (
        descriptor.location
        == ProviderLocation.local
    )