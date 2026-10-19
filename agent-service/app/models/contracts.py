from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelContract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )


class ProviderLocation(str, Enum):
    local = "local"
    remote = "remote"


class ModelHealthStatus(str, Enum):
    healthy = "healthy"
    degraded = "degraded"
    unavailable = "unavailable"
    unknown = "unknown"


class ModelMessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ModelMessage(ModelContract):
    role: ModelMessageRole

    content: str = Field(
        min_length=1,
        max_length=100_000,
    )


class ModelRequest(ModelContract):
    schema_version: Literal["ModelRequest.v1"] = (
        "ModelRequest.v1"
    )

    messages: list[ModelMessage] = Field(
        min_length=1,
        max_length=100,
    )

    model: str | None = Field(
        default=None,
        max_length=200,
    )

    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
    )

    max_output_tokens: int | None = Field(
        default=None,
        ge=1,
        le=1_000_000,
    )

    response_format: Literal[
        "text",
        "json",
    ] = "text"

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        max_length=25,
    )


class ModelUsage(ModelContract):
    input_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    output_tokens: int | None = Field(
        default=None,
        ge=0,
    )

    total_tokens: int | None = Field(
        default=None,
        ge=0,
    )


class ModelResponse(ModelContract):
    schema_version: Literal["ModelResponse.v1"] = (
        "ModelResponse.v1"
    )

    text: str

    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )

    model: str = Field(
        min_length=1,
        max_length=200,
    )

    usage: ModelUsage = Field(
        default_factory=ModelUsage,
    )

    finish_reason: str | None = Field(
        default=None,
        max_length=100,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        max_length=25,
    )


class ModelStreamChunk(ModelContract):
    schema_version: Literal["ModelStreamChunk.v1"] = (
        "ModelStreamChunk.v1"
    )

    delta: str

    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )

    model: str = Field(
        min_length=1,
        max_length=200,
    )

    finish_reason: str | None = Field(
        default=None,
        max_length=100,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        max_length=25,
    )


class ModelHealth(ModelContract):
    schema_version: Literal["ModelHealth.v1"] = (
        "ModelHealth.v1"
    )

    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )

    status: ModelHealthStatus

    latency_ms: float | None = Field(
        default=None,
        ge=0.0,
    )

    message: str | None = Field(
        default=None,
        max_length=500,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        max_length=25,
    )


class ModelCapabilities(ModelContract):
    schema_version: Literal["ModelCapabilities.v1"] = (
        "ModelCapabilities.v1"
    )

    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )

    model: str | None = Field(
        default=None,
        max_length=200,
    )

    location: ProviderLocation

    text_generation: bool = True
    streaming: bool = False
    json_mode: bool = False
    tools: bool = False
    vision: bool = False
    embeddings: bool = False

    context_length: int | None = Field(
        default=None,
        ge=1,
    )


class ModelCostEstimate(ModelContract):
    """
    Estimated provider fee only.

    A local model may have zero provider fee while still consuming
    device compute, electricity, memory, and battery.
    """

    schema_version: Literal["ModelCostEstimate.v1"] = (
        "ModelCostEstimate.v1"
    )

    provider_id: str = Field(
        min_length=1,
        max_length=100,
    )

    model: str = Field(
        min_length=1,
        max_length=200,
    )

    local: bool

    estimated_provider_cost: Decimal | None = Field(
        default=None,
        ge=0,
    )

    currency: str = Field(
        default="GBP",
        min_length=3,
        max_length=3,
    )

    pricing_available: bool = False

    reason_codes: list[str] = Field(
        default_factory=list,
        max_length=20,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        max_length=25,
    )


class ModelProviderDescriptor(ModelContract):
    provider_id: str = Field(
        pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$"
    )

    location: ProviderLocation

    default_model: str | None = Field(
        default=None,
        max_length=200,
    )

    supports_json: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_vision: bool = False
    supports_embeddings: bool = False