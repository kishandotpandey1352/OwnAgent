from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.contracts import (
    ModelProviderDescriptor,
    ModelRequest,
    ModelResponse,
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