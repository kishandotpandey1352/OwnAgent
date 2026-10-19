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

from collections.abc import Iterator
from decimal import Decimal

from app.models.contracts import (
    ModelCapabilities,
    ModelCostEstimate,
    ModelHealth,
    ModelHealthStatus,
    ModelMessage,
    ModelMessageRole,
    ModelProviderDescriptor,
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
    ModelUsage,
    ProviderLocation,
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

    def stream(
    self,
    request: ModelRequest,
) -> Iterator[ModelStreamChunk]:
        model_name = (
            request.model
            or self.descriptor.default_model
            or "fake-model"
        )

        yield ModelStreamChunk(
            delta="fake ",
            provider_id=(
                self._response_provider_id
            ),
            model=model_name,
        )

        yield ModelStreamChunk(
            delta="response",
            provider_id=(
                self._response_provider_id
            ),
            model=model_name,
            finish_reason="stop",
        )


    def health(
        self,
    ) -> ModelHealth:
        return ModelHealth(
            provider_id=(
                self._response_provider_id
            ),
            status=ModelHealthStatus.healthy,
            latency_ms=1.0,
        )


    def capabilities(
        self,
        model: str | None = None,
    ) -> ModelCapabilities:
        return ModelCapabilities(
            provider_id=(
                self._response_provider_id
            ),
            model=(
                model
                or self.descriptor.default_model
            ),
            location=(
                self.descriptor.location
            ),
            text_generation=True,
            streaming=True,
        )


    def estimate(
        self,
        request: ModelRequest,
    ) -> ModelCostEstimate:
        return ModelCostEstimate(
            provider_id=(
                self._response_provider_id
            ),
            model=(
                request.model
                or self.descriptor.default_model
                or "fake-model"
            ),
            local=(
                self.descriptor.location
                == ProviderLocation.local
            ),
            estimated_provider_cost=(
                Decimal("0")
                if (
                    self.descriptor.location
                    == ProviderLocation.local
                )
                else Decimal("0.01")
            ),
            currency="GBP",
            pricing_available=True,
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


def test_gateway_health_uses_selected_provider():
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
    )

    result = gateway.health(
        provider_id="local-test"
    )

    assert result.provider_id == "local-test"
    assert (
        result.status
        == ModelHealthStatus.healthy
    )


def test_gateway_capabilities_use_selected_provider():
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
    )

    result = gateway.capabilities(
        provider_id="local-test",
        model="test-model",
    )

    assert result.provider_id == "local-test"
    assert result.model == "test-model"
    assert result.streaming is True


def test_gateway_estimate_uses_selected_provider():
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
    )

    result = gateway.estimate(
        provider_id="local-test",
        request=make_request(),
    )

    assert result.provider_id == "local-test"
    assert result.local is True
    assert (
        result.estimated_provider_cost
        == Decimal("0")
    )


def test_gateway_stream_uses_selected_provider():
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
    )

    chunks = list(
        gateway.stream(
            provider_id="local-test",
            request=make_request(),
        )
    )

    assert len(chunks) == 2

    assert (
        "".join(
            chunk.delta
            for chunk in chunks
        )
        == "fake response"
    )

    assert all(
        chunk.provider_id == "local-test"
        for chunk in chunks
    )