from __future__ import annotations

from app.models.contracts import (
    ModelRequest,
    ModelResponse,
)
from app.models.errors import (
    ModelProviderContractError,
    ModelProviderNotFoundError,
)
from app.models.registry import (
    ModelProviderRegistry,
)


class ModelGateway:
    """
    Single execution boundary for model inference.

    Callers select a logical provider ID.
    They do not instantiate provider SDK clients directly.
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


    def generate(
        self,
        *,
        request: ModelRequest,
        provider_id: str | None = None,
    ) -> ModelResponse:
        selected_provider_id = (
            self.resolve_provider_id(
                provider_id
            )
        )

        provider = self._registry.get(
            selected_provider_id
        )

        response = provider.generate(
            request
        )

        expected_provider_id = (
            provider
            .descriptor
            .provider_id
        )

        if (
            response.provider_id
            != expected_provider_id
        ):
            raise ModelProviderContractError(
                "Provider returned a response "
                "with a mismatched provider_id. "
                f"expected={expected_provider_id!r} "
                f"actual={response.provider_id!r}"
            )

        return response