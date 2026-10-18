from __future__ import annotations

from collections.abc import Iterable

from app.models.contracts import (
    ModelProviderDescriptor,
)
from app.models.errors import (
    ModelProviderAlreadyRegisteredError,
    ModelProviderNotFoundError,
)
from app.models.provider import ModelProvider


class ModelProviderRegistry:
    """
    Server-owned registry of available model providers.

    Model/provider IDs supplied by users or agents can only resolve
    to providers registered here.
    """

    def __init__(
        self,
        providers: Iterable[ModelProvider] = (),
    ) -> None:
        self._providers: dict[
            str,
            ModelProvider,
        ] = {}

        for provider in providers:
            self.register(provider)


    def register(
        self,
        provider: ModelProvider,
        *,
        replace: bool = False,
    ) -> None:
        provider_id = (
            provider
            .descriptor
            .provider_id
        )

        if (
            provider_id in self._providers
            and not replace
        ):
            raise ModelProviderAlreadyRegisteredError(
                f"Model provider already registered: "
                f"{provider_id}"
            )

        self._providers[
            provider_id
        ] = provider


    def get(
        self,
        provider_id: str,
    ) -> ModelProvider:
        provider = self._providers.get(
            provider_id
        )

        if provider is None:
            raise ModelProviderNotFoundError(
                f"Model provider is not registered: "
                f"{provider_id}"
            )

        return provider


    def contains(
        self,
        provider_id: str,
    ) -> bool:
        return provider_id in self._providers


    def list_descriptors(
        self,
    ) -> list[ModelProviderDescriptor]:
        return [
            provider.descriptor
            for provider
            in self._providers.values()
        ]


    def provider_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            self._providers.keys()
        )