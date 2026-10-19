from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from app.models.contracts import (
    ModelCapabilities,
    ModelCostEstimate,
    ModelHealth,
    ModelProviderDescriptor,
    ModelRequest,
    ModelResponse,
    ModelStreamChunk,
)


@runtime_checkable
class ModelProvider(Protocol):
    """
    Stable provider boundary used by OwnAgent.

    Provider-specific SDKs must remain behind implementations
    of this interface.
    """

    @property
    def descriptor(
        self,
    ) -> ModelProviderDescriptor:
        ...


    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        ...


    def stream(
        self,
        request: ModelRequest,
    ) -> Iterator[ModelStreamChunk]:
        ...


    def health(
        self,
    ) -> ModelHealth:
        ...


    def capabilities(
        self,
        model: str | None = None,
    ) -> ModelCapabilities:
        ...


    def estimate(
        self,
        request: ModelRequest,
    ) -> ModelCostEstimate:
        ...