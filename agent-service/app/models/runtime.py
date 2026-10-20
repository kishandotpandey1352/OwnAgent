from __future__ import annotations

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.models.gateway import ModelGateway
from app.models.providers.ollama import (
    OllamaProvider,
)
from app.models.providers.openai import (
    OpenAIChatProvider,
)
from app.models.registry import (
    ModelProviderRegistry,
)
from app.models.contracts import (
    ProviderLocation,
)

from app.models.providers.openai_compatible import (
    OpenAICompatibleProvider,
)



OPENAI_PREMIUM_PROVIDER_ID = "openai-premium"

OLLAMA_LOCAL_PROVIDER_ID = "ollama-local"

LMSTUDIO_LOCAL_PROVIDER_ID = "lmstudio-local"

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

    if settings.ollama_enabled:
        registry.register(
            OllamaProvider(
                provider_id=(
                    OLLAMA_LOCAL_PROVIDER_ID
                ),
                base_url=(
                    settings.ollama_base_url
                ),
                default_model=(
                    settings.ollama_default_model
                ),
                timeout_seconds=(
                    settings.ollama_timeout_seconds
                ),
            )
        )

    if settings.lmstudio_enabled:
        registry.register(
            OpenAICompatibleProvider(
                provider_id=(
                    LMSTUDIO_LOCAL_PROVIDER_ID
                ),
                base_url=(
                    settings.lmstudio_base_url
                ),
                default_model=(
                    settings.lmstudio_default_model
                ),
                api_key=(
                    settings.lmstudio_api_key
                ),
                location=(
                    ProviderLocation.local
                ),
                timeout_seconds=(
                    settings.lmstudio_timeout_seconds
                ),
            )
        )

    return ModelGateway(
        registry=registry,
        default_provider_id=(
            OPENAI_PREMIUM_PROVIDER_ID
        ),
    )