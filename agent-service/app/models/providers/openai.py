from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI

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
from app.models.errors import (
    ModelProviderContractError,
    ModelProviderInvocationError,
)


class OpenAIChatProvider:
    """
    OpenAI adapter behind OwnAgent's generic ModelProvider boundary.

    No agent, node, coordinator, workflow, or product pack should need
    to know that LangChain/ChatOpenAI is used underneath.
    """

    def __init__(
        self,
        *,
        provider_id: str,
        api_key: str,
        default_model: str,
    ) -> None:
        self._api_key = api_key

        self._descriptor = ModelProviderDescriptor(
            provider_id=provider_id,
            location=ProviderLocation.remote,
            default_model=default_model,
            supports_json=False,
            supports_streaming=True,
            supports_tools=False,
            supports_vision=False,
            supports_embeddings=False,
        )


    @property
    def descriptor(
        self,
    ) -> ModelProviderDescriptor:
        return self._descriptor


    def _resolve_model_name(
        self,
        request: ModelRequest,
    ) -> str:
        model_name = (
            request.model
            or self.descriptor.default_model
        )

        if not model_name:
            raise ModelProviderContractError(
                "No OpenAI model was configured."
            )

        return model_name


    def _convert_message(
        self,
        message: ModelMessage,
    ) -> BaseMessage:
        if message.role == ModelMessageRole.system:
            return SystemMessage(
                content=message.content
            )

        if message.role == ModelMessageRole.user:
            return HumanMessage(
                content=message.content
            )

        if message.role == ModelMessageRole.assistant:
            return AIMessage(
                content=message.content
            )

        raise ModelProviderContractError(
            "OpenAIChatProvider does not currently support "
            f"message role {message.role.value!r}."
        )


    @staticmethod
    def _usage_value(
        usage: Any,
        key: str,
    ) -> int | None:
        if not isinstance(
            usage,
            dict,
        ):
            return None

        value = usage.get(
            key
        )

        if (
            isinstance(value, int)
            and value >= 0
        ):
            return value

        return None


    def _validate_request(
        self,
        request: ModelRequest,
    ) -> None:
        if not self._api_key:
            raise ModelProviderInvocationError(
                "OPENAI_API_KEY is required for the "
                "configured OpenAI provider."
            )

        if request.response_format != "text":
            raise ModelProviderContractError(
                "OpenAI JSON response mode has not yet "
                "been enabled through the OwnAgent "
                "model boundary."
            )


    def _build_model(
        self,
        *,
        model_name: str,
        request: ModelRequest,
    ) -> ChatOpenAI:
        return ChatOpenAI(
            model=model_name,
            temperature=(
                request.temperature
                if request.temperature is not None
                else 0.2
            ),
            api_key=self._api_key,
        )


    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        self._validate_request(
            request
        )

        model_name = self._resolve_model_name(
            request
        )

        messages = [
            self._convert_message(message)
            for message in request.messages
        ]

        try:
            model = self._build_model(
                model_name=model_name,
                request=request,
            )

            response = model.invoke(
                messages
            )

        except (
            ModelProviderContractError,
            ModelProviderInvocationError,
        ):
            raise

        except Exception as exc:
            raise ModelProviderInvocationError(
                "OpenAI model invocation failed."
            ) from exc

        content = response.content

        if not isinstance(
            content,
            str,
        ):
            content = str(
                content
            )

        usage_metadata = getattr(
            response,
            "usage_metadata",
            None,
        )

        response_metadata = getattr(
            response,
            "response_metadata",
            {},
        )

        if not isinstance(
            response_metadata,
            dict,
        ):
            response_metadata = {}

        return ModelResponse(
            text=content,
            provider_id=(
                self.descriptor.provider_id
            ),
            model=model_name,
            usage=ModelUsage(
                input_tokens=self._usage_value(
                    usage_metadata,
                    "input_tokens",
                ),
                output_tokens=self._usage_value(
                    usage_metadata,
                    "output_tokens",
                ),
                total_tokens=self._usage_value(
                    usage_metadata,
                    "total_tokens",
                ),
            ),
            finish_reason=(
                response_metadata.get(
                    "finish_reason"
                )
            ),
        )


    def stream(
        self,
        request: ModelRequest,
    ) -> Iterator[ModelStreamChunk]:
        self._validate_request(
            request
        )

        model_name = self._resolve_model_name(
            request
        )

        messages = [
            self._convert_message(message)
            for message in request.messages
        ]

        try:
            model = self._build_model(
                model_name=model_name,
                request=request,
            )

            for chunk in model.stream(
                messages
            ):
                content = chunk.content

                if not isinstance(
                    content,
                    str,
                ):
                    content = str(
                        content
                    )

                response_metadata = getattr(
                    chunk,
                    "response_metadata",
                    {},
                )

                if not isinstance(
                    response_metadata,
                    dict,
                ):
                    response_metadata = {}

                yield ModelStreamChunk(
                    delta=content,
                    provider_id=(
                        self.descriptor.provider_id
                    ),
                    model=model_name,
                    finish_reason=(
                        response_metadata.get(
                            "finish_reason"
                        )
                    ),
                )

        except (
            ModelProviderContractError,
            ModelProviderInvocationError,
        ):
            raise

        except Exception as exc:
            raise ModelProviderInvocationError(
                "OpenAI streaming invocation failed."
            ) from exc


    def health(
        self,
    ) -> ModelHealth:
        if not self._api_key:
            return ModelHealth(
                provider_id=(
                    self.descriptor.provider_id
                ),
                status=(
                    ModelHealthStatus.unavailable
                ),
                message=(
                    "OpenAI provider is not configured "
                    "with an API key."
                ),
            )

        # W02-MODEL-01 reports configuration readiness.
        # A live provider probe can be added in W02-PROV-04.
        return ModelHealth(
            provider_id=(
                self.descriptor.provider_id
            ),
            status=ModelHealthStatus.unknown,
            message=(
                "OpenAI provider is configured. "
                "Live provider health has not been probed."
            ),
        )


    def capabilities(
        self,
        model: str | None = None,
    ) -> ModelCapabilities:
        return ModelCapabilities(
            provider_id=(
                self.descriptor.provider_id
            ),
            model=(
                model
                or self.descriptor.default_model
            ),
            location=(
                self.descriptor.location
            ),
            text_generation=True,
            streaming=(
                self.descriptor.supports_streaming
            ),
            json_mode=(
                self.descriptor.supports_json
            ),
            tools=(
                self.descriptor.supports_tools
            ),
            vision=(
                self.descriptor.supports_vision
            ),
            embeddings=(
                self.descriptor.supports_embeddings
            ),
            context_length=None,
        )


    def estimate(
        self,
        request: ModelRequest,
    ) -> ModelCostEstimate:
        model_name = self._resolve_model_name(
            request
        )

        # Pricing becomes registry-driven later in Week 2.
        # Do not invent a price here.
        return ModelCostEstimate(
            provider_id=(
                self.descriptor.provider_id
            ),
            model=model_name,
            local=False,
            estimated_provider_cost=None,
            currency="GBP",
            pricing_available=False,
            reason_codes=[
                "PRICING_METADATA_UNAVAILABLE"
            ],
        )