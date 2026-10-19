from __future__ import annotations

from typing import Any

from app.models.contracts import (
    ModelMessage,
    ModelMessageRole,
    ModelRequest,
    ModelResponse,
)
from app.models.runtime import get_model_gateway


def generate_text(
    *,
    system_prompt: str,
    user_prompt: str,
    provider_id: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    purpose: str,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ModelResponse:
    """
    Convenience boundary for normal text-generation operations.

    Application code should not instantiate provider SDK clients.
    """

    invocation_metadata: dict[str, Any] = {
        "purpose": purpose,
    }

    if request_id:
        invocation_metadata[
            "request_id"
        ] = request_id

    if metadata:
        invocation_metadata.update(
            metadata
        )

    return get_model_gateway().generate(
        provider_id=provider_id,
        request=ModelRequest(
            messages=[
                ModelMessage(
                    role=ModelMessageRole.system,
                    content=system_prompt,
                ),
                ModelMessage(
                    role=ModelMessageRole.user,
                    content=user_prompt,
                ),
            ],
            model=model,
            temperature=temperature,
            response_format="text",
            metadata=invocation_metadata,
        ),
    )