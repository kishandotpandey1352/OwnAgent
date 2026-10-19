from __future__ import annotations

from collections.abc import Iterator

from app.models.contracts import (
    ModelCapabilities,
    ModelCostEstimate,
    ModelHealth,
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
)
from app.models.errors import (
    ModelProviderContractError,
    ModelProviderNotFoundError,
)
from app.models.provider import ModelProvider
from app.models.registry import (
    ModelProviderRegistry,
)


class ModelGateway:
    """
    Single execution boundary for model operations.

    Callers select a logical provider ID.
    They never instantiate provider SDK clients directly.
    """

    def __init__(
        self,
        *,
        registry: ModelProviderRegistry,
        default_provider_id: str | None = None,
    ) -> None:
        self._registry = registry
        self._default_provider_id = (
            default_provider_id
        )


    def resolve_provider_id(
        self,
        provider_id: str | None,
    ) -> str:
        selected = (
            provider_id
            or self._default_provider_id
        )

        if not selected:
            raise ModelProviderNotFoundError(
                "No model provider was selected "
                "and no default provider is configured."
            )

        return selected

    def has_provider(
        self,
        provider_id: str,
    ) -> bool:
        return self._registry.contains(
            provider_id
        )


    def _resolve_provider(
        self,
        provider_id: str | None,
    ) -> tuple[str, ModelProvider]:
        selected_provider_id = (
            self.resolve_provider_id(
                provider_id
            )
        )

        provider = self._registry.get(
            selected_provider_id
        )

        return (
            selected_provider_id,
            provider,
        )


    @staticmethod
    def _validate_provider_identity(
        *,
        expected_provider_id: str,
        actual_provider_id: str,
        operation: str,
    ) -> None:
        if actual_provider_id != expected_provider_id:
            raise ModelProviderContractError(
                f"Provider returned {operation} data "
                "with a mismatched provider_id. "
                f"expected={expected_provider_id!r} "
                f"actual={actual_provider_id!r}"
            )


    def generate(
        self,
        *,
        request: ModelRequest,
        provider_id: str | None = None,
    ) -> ModelResponse:
        (
            selected_provider_id,
            provider,
        ) = self._resolve_provider(
            provider_id
        )

        response = provider.generate(
            request
        )

        self._validate_provider_identity(
            expected_provider_id=selected_provider_id,
            actual_provider_id=response.provider_id,
            operation="response",
        )

        return response


    def stream(
        self,
        *,
        request: ModelRequest,
        provider_id: str | None = None,
    ) -> Iterator[ModelStreamChunk]:
        (
            selected_provider_id,
            provider,
        ) = self._resolve_provider(
            provider_id
        )

        def iterator() -> Iterator[ModelStreamChunk]:
            for chunk in provider.stream(
                request
            ):
                self._validate_provider_identity(
                    expected_provider_id=(
                        selected_provider_id
                    ),
                    actual_provider_id=(
                        chunk.provider_id
                    ),
                    operation="stream",
                )

                yield chunk

        return iterator()


    def health(
        self,
        *,
        provider_id: str | None = None,
    ) -> ModelHealth:
        (
            selected_provider_id,
            provider,
        ) = self._resolve_provider(
            provider_id
        )

        result = provider.health()

        self._validate_provider_identity(
            expected_provider_id=selected_provider_id,
            actual_provider_id=result.provider_id,
            operation="health",
        )

        return result


    def capabilities(
        self,
        *,
        provider_id: str | None = None,
        model: str | None = None,
    ) -> ModelCapabilities:
        (
            selected_provider_id,
            provider,
        ) = self._resolve_provider(
            provider_id
        )

        result = provider.capabilities(
            model=model
        )

        self._validate_provider_identity(
            expected_provider_id=selected_provider_id,
            actual_provider_id=result.provider_id,
            operation="capability",
        )

        return result


    def estimate(
        self,
        *,
        request: ModelRequest,
        provider_id: str | None = None,
    ) -> ModelCostEstimate:
        (
            selected_provider_id,
            provider,
        ) = self._resolve_provider(
            provider_id
        )

        result = provider.estimate(
            request
        )

        self._validate_provider_identity(
            expected_provider_id=selected_provider_id,
            actual_provider_id=result.provider_id,
            operation="estimate",
        )

        return result