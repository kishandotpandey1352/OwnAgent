from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.models.gateway import ModelGateway
from app.models.providers.openai import (
    OpenAIChatProvider,
)
from app.models.registry import (
    ModelProviderRegistry,
)


OPENAI_PREMIUM_PROVIDER_ID = "openai-premium"


@lru_cache(maxsize=1)
def get_model_gateway() -> ModelGateway:
    """
    Build the application model gateway once per process.

    Provider configuration is server-owned. Callers select only
    registered logical provider IDs.
    """

    registry = ModelProviderRegistry()

    registry.register(
        OpenAIChatProvider(
            provider_id=OPENAI_PREMIUM_PROVIDER_ID,
            api_key=(
                settings.openai_api_key
                or ""
            ),
            default_model=settings.agent_model,
        )
    )

    return ModelGateway(
        registry=registry,
        default_provider_id=(
            OPENAI_PREMIUM_PROVIDER_ID
        ),
    )