from __future__ import annotations

import json
import time
from collections.abc import Iterator
from decimal import Decimal

import httpx

from app.models.contracts import (
    ModelCapabilities,
    ModelCostEstimate,
    ModelHealth,
    ModelHealthStatus,
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


class OpenAICompatibleProvider:
    """
    Generic adapter for OpenAI-compatible chat-completion servers.

    LM Studio is the first OwnAgent configuration of this adapter.

    The base URL, model ID and credentials are trusted application
    configuration. They are not selected from arbitrary model output.
    """

    def __init__(
        self,
        *,
        provider_id: str,
        base_url: str,
        default_model: str | None = None,
        api_key: str | None = None,
        location: ProviderLocation = ProviderLocation.local,
        timeout_seconds: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = self._validate_base_url(
            base_url
        )
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._transport = transport

        self._descriptor = ModelProviderDescriptor(
            provider_id=provider_id,
            location=location,
            default_model=default_model,

            # Keep capabilities conservative until
            # model-specific registry metadata exists.
            supports_json=False,
            supports_streaming=True,
            supports_tools=False,
            supports_vision=False,
            supports_embeddings=False,
        )


    @staticmethod
    def _validate_base_url(
        base_url: str,
    ) -> str:
        value = base_url.strip().rstrip("/")

        if not value:
            raise ModelProviderContractError(
                "OpenAI-compatible base URL is required."
            )

        try:
            url = httpx.URL(
                value
            )

        except Exception as exc:
            raise ModelProviderContractError(
                "OpenAI-compatible base URL is invalid."
            ) from exc

        if url.scheme not in {
            "http",
            "https",
        }:
            raise ModelProviderContractError(
                "OpenAI-compatible base URL must use "
                "http or https."
            )

        if not url.host:
            raise ModelProviderContractError(
                "OpenAI-compatible base URL must "
                "contain a host."
            )

        return value


    @property
    def descriptor(
        self,
    ) -> ModelProviderDescriptor:
        return self._descriptor


    def _client(
        self,
    ) -> httpx.Client:
        headers = {
            "Accept": "application/json",
        }

        if self._api_key:
            headers["Authorization"] = (
                f"Bearer {self._api_key}"
            )

        # Trailing slash is deliberate.
        # Relative paths then preserve /v1 in:
        # http://127.0.0.1:1234/v1/
        return httpx.Client(
            base_url=f"{self._base_url}/",
            timeout=self._timeout_seconds,
            headers=headers,
            transport=self._transport,
        )


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
                "No model was selected for the "
                "OpenAI-compatible provider. "
                "Provide request.model or configure "
                "a default model."
            )

        return model_name


    @staticmethod
    def _normalise_messages(
        request: ModelRequest,
    ) -> list[dict[str, str]]:
        messages: list[
            dict[str, str]
        ] = []

        for message in request.messages:
            if (
                message.role
                == ModelMessageRole.tool
            ):
                # OwnAgent's generic ModelMessage does not
                # yet carry tool_call_id/tool-result metadata.
                raise ModelProviderContractError(
                    "Tool-role messages are not yet "
                    "supported by the OpenAI-compatible "
                    "OwnAgent boundary."
                )

            messages.append(
                {
                    "role": message.role.value,
                    "content": message.content,
                }
            )

        return messages


    def _validate_request(
        self,
        request: ModelRequest,
    ) -> None:
        # Different OpenAI-compatible servers vary in
        # JSON response-format support. Keep the platform
        # contract conservative for W02-PROV-03.
        if request.response_format != "text":
            raise ModelProviderContractError(
                "JSON response mode has not yet been "
                "enabled for the generic "
                "OpenAI-compatible provider."
            )


    def _build_payload(
        self,
        *,
        request: ModelRequest,
        model_name: str,
        stream: bool,
    ) -> dict:
        payload: dict = {
            "model": model_name,
            "messages": self._normalise_messages(
                request
            ),
            "stream": stream,
        }

        if request.temperature is not None:
            payload["temperature"] = (
                request.temperature
            )

        if request.max_output_tokens is not None:
            payload["max_tokens"] = (
                request.max_output_tokens
            )

        return payload


    @staticmethod
    def _token_value(
        usage: object,
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


    @staticmethod
    def _first_choice(
        data: dict,
    ) -> dict:
        choices = data.get(
            "choices"
        )

        if (
            not isinstance(choices, list)
            or not choices
            or not isinstance(
                choices[0],
                dict,
            )
        ):
            raise ModelProviderContractError(
                "OpenAI-compatible response did not "
                "contain a valid choices array."
            )

        return choices[0]


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

        payload = self._build_payload(
            request=request,
            model_name=model_name,
            stream=False,
        )

        try:
            with self._client() as client:
                response = client.post(
                    "chat/completions",
                    json=payload,
                )

                response.raise_for_status()

                data = response.json()

        except (
            ModelProviderContractError,
            ModelProviderInvocationError,
        ):
            raise

        except (
            httpx.HTTPError,
            ValueError,
        ) as exc:
            raise ModelProviderInvocationError(
                "OpenAI-compatible model invocation "
                "failed."
            ) from exc

        if not isinstance(
            data,
            dict,
        ):
            raise ModelProviderContractError(
                "OpenAI-compatible response must "
                "be a JSON object."
            )

        if data.get("error"):
            raise ModelProviderInvocationError(
                "OpenAI-compatible provider returned "
                "an inference error."
            )

        choice = self._first_choice(
            data
        )

        message = choice.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            raise ModelProviderContractError(
                "OpenAI-compatible response did not "
                "contain a valid message."
            )

        content = message.get(
            "content"
        )

        if not isinstance(
            content,
            str,
        ):
            raise ModelProviderContractError(
                "OpenAI-compatible response message "
                "did not contain text content."
            )

        response_model = data.get(
            "model"
        )

        if not isinstance(
            response_model,
            str,
        ):
            response_model = model_name

        usage = data.get(
            "usage"
        )

        return ModelResponse(
            text=content,
            provider_id=(
                self.descriptor.provider_id
            ),
            model=response_model,
            usage=ModelUsage(
                input_tokens=self._token_value(
                    usage,
                    "prompt_tokens",
                ),
                output_tokens=self._token_value(
                    usage,
                    "completion_tokens",
                ),
                total_tokens=self._token_value(
                    usage,
                    "total_tokens",
                ),
            ),
            finish_reason=(
                choice.get(
                    "finish_reason"
                )
                if isinstance(
                    choice.get(
                        "finish_reason"
                    ),
                    str,
                )
                else None
            ),
            metadata={
                "openai_compatible": True,
            },
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

        payload = self._build_payload(
            request=request,
            model_name=model_name,
            stream=True,
        )

        try:
            with self._client() as client:
                with client.stream(
                    "POST",
                    "chat/completions",
                    json=payload,
                ) as response:

                    response.raise_for_status()

                    for line in response.iter_lines():
                        if not line:
                            continue

                        line = line.strip()

                        if not line:
                            continue

                        if not line.startswith(
                            "data:"
                        ):
                            continue

                        raw_data = (
                            line[len("data:"):]
                            .strip()
                        )

                        if raw_data == "[DONE]":
                            break

                        try:
                            data = json.loads(
                                raw_data
                            )

                        except json.JSONDecodeError as exc:
                            raise ModelProviderContractError(
                                "OpenAI-compatible stream "
                                "returned invalid JSON."
                            ) from exc

                        if not isinstance(
                            data,
                            dict,
                        ):
                            raise ModelProviderContractError(
                                "OpenAI-compatible stream "
                                "event must be an object."
                            )

                        if data.get("error"):
                            raise ModelProviderInvocationError(
                                "OpenAI-compatible provider "
                                "returned a streaming error."
                            )

                        choice = self._first_choice(
                            data
                        )

                        delta = choice.get(
                            "delta"
                        )

                        if not isinstance(
                            delta,
                            dict,
                        ):
                            delta = {}

                        content = delta.get(
                            "content"
                        )

                        if content is None:
                            content = ""

                        if not isinstance(
                            content,
                            str,
                        ):
                            content = str(
                                content
                            )

                        finish_reason = (
                            choice.get(
                                "finish_reason"
                            )
                        )

                        if not isinstance(
                            finish_reason,
                            str,
                        ):
                            finish_reason = None

                        chunk_model = data.get(
                            "model"
                        )

                        if not isinstance(
                            chunk_model,
                            str,
                        ):
                            chunk_model = model_name

                        if (
                            content
                            or finish_reason
                        ):
                            yield ModelStreamChunk(
                                delta=content,
                                provider_id=(
                                    self.descriptor.provider_id
                                ),
                                model=chunk_model,
                                finish_reason=(
                                    finish_reason
                                ),
                                metadata={
                                    "openai_compatible": True,
                                },
                            )

        except (
            ModelProviderContractError,
            ModelProviderInvocationError,
        ):
            raise

        except httpx.HTTPError as exc:
            raise ModelProviderInvocationError(
                "OpenAI-compatible streaming "
                "invocation failed."
            ) from exc


    def health(
        self,
    ) -> ModelHealth:
        started = time.perf_counter()

        try:
            with self._client() as client:
                response = client.get(
                    "models"
                )

                response.raise_for_status()

                data = response.json()

            latency_ms = (
                time.perf_counter()
                - started
            ) * 1000.0

            model_count = 0

            if isinstance(
                data,
                dict,
            ):
                models = data.get(
                    "data"
                )

                if isinstance(
                    models,
                    list,
                ):
                    model_count = len(
                        models
                    )

            return ModelHealth(
                provider_id=(
                    self.descriptor.provider_id
                ),
                status=(
                    ModelHealthStatus.healthy
                ),
                latency_ms=latency_ms,
                message=(
                    "OpenAI-compatible provider "
                    "is reachable."
                ),
                metadata={
                    "model_count": model_count,
                },
            )

        except (
            httpx.HTTPError,
            ValueError,
        ):
            latency_ms = (
                time.perf_counter()
                - started
            ) * 1000.0

            return ModelHealth(
                provider_id=(
                    self.descriptor.provider_id
                ),
                status=(
                    ModelHealthStatus.unavailable
                ),
                latency_ms=latency_ms,
                message=(
                    "OpenAI-compatible provider "
                    "is not reachable."
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
            streaming=True,

            # Conservative until W02-REG-05 supplies
            # per-model capability metadata.
            json_mode=False,
            tools=False,
            vision=False,
            embeddings=False,
            context_length=None,
        )


    def estimate(
        self,
        request: ModelRequest,
    ) -> ModelCostEstimate:
        model_name = self._resolve_model_name(
            request
        )

        is_local = (
            self.descriptor.location
            == ProviderLocation.local
        )

        if is_local:
            return ModelCostEstimate(
                provider_id=(
                    self.descriptor.provider_id
                ),
                model=model_name,
                local=True,
                estimated_provider_cost=(
                    Decimal("0")
                ),
                currency="GBP",
                pricing_available=True,
                reason_codes=[
                    "LOCAL_PROVIDER_NO_PROVIDER_FEE"
                ],
                metadata={
                    "device_compute_not_included":
                        True,
                },
            )

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