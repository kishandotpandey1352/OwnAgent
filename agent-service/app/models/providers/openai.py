from __future__ import annotations

from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_openai import ChatOpenAI

from app.models.contracts import (
    ModelMessage,
    ModelMessageRole,
    ModelProviderDescriptor,
    ModelRequest,
    ModelResponse,
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

    No agent, node, coordinator, or workflow should need to know
    that LangChain/ChatOpenAI is used underneath.
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
            supports_streaming=False,
            supports_tools=False,
        )

    @property
    def descriptor(
        self,
    ) -> ModelProviderDescriptor:
        return self._descriptor

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
        if not isinstance(usage, dict):
            return None

        value = usage.get(key)

        if isinstance(value, int) and value >= 0:
            return value

        return None

    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        if not self._api_key:
            raise ModelProviderInvocationError(
                "OPENAI_API_KEY is required for the "
                "configured OpenAI provider."
            )

        model_name = (
            request.model
            or self.descriptor.default_model
        )

        if not model_name:
            raise ModelProviderContractError(
                "No OpenAI model was configured."
            )

        if request.response_format != "text":
            raise ModelProviderContractError(
                "OpenAI JSON response mode has not yet "
                "been enabled through the OwnAgent model boundary."
            )

        messages = [
            self._convert_message(message)
            for message in request.messages
        ]

        try:
            model = ChatOpenAI(
                model=model_name,
                temperature=(
                    request.temperature
                    if request.temperature is not None
                    else 0.2
                ),
                api_key=self._api_key,
            )

            response = model.invoke(
                messages
            )

        except ModelProviderContractError:
            raise

        except Exception as exc:
            raise ModelProviderInvocationError(
                "OpenAI model invocation failed."
            ) from exc

        content = response.content

        if not isinstance(content, str):
            content = str(content)

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

        if not isinstance(response_metadata, dict):
            response_metadata = {}

        return ModelResponse(
            text=content,
            provider_id=self.descriptor.provider_id,
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
            finish_reason=response_metadata.get(
                "finish_reason"
            ),
        )