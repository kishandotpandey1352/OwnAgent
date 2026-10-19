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


class OllamaProvider:
    """
    Local Ollama model provider.

    Provider-specific HTTP/API behaviour remains isolated here.
    Agents, workflows and product packs must use ModelGateway
    instead of communicating with Ollama directly.
    """

    def __init__(
        self,
        *,
        provider_id: str,
        base_url: str,
        default_model: str | None = None,
        timeout_seconds: float = 120.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

        self._descriptor = ModelProviderDescriptor(
            provider_id=provider_id,
            location=ProviderLocation.local,
            default_model=default_model,
            supports_json=True,
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


    def _client(
        self,
    ) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
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
                "No Ollama model was selected. "
                "Provide request.model or configure "
                "ollama_default_model."
            )

        return model_name


    @staticmethod
    def _normalise_messages(
        request: ModelRequest,
    ) -> list[dict[str, str]]:
        return [
            {
                "role": message.role.value,
                "content": message.content,
            }
            for message in request.messages
        ]


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

        options: dict = {}

        if request.temperature is not None:
            options["temperature"] = (
                request.temperature
            )

        if request.max_output_tokens is not None:
            options["num_predict"] = (
                request.max_output_tokens
            )

        if options:
            payload["options"] = options

        if request.response_format == "json":
            payload["format"] = "json"

        return payload


    @staticmethod
    def _token_count(
        value: object,
    ) -> int | None:
        if (
            isinstance(value, int)
            and value >= 0
        ):
            return value

        return None


    @staticmethod
    def _finish_reason(
        data: dict,
    ) -> str | None:
        explicit_reason = data.get(
            "done_reason"
        )

        if isinstance(
            explicit_reason,
            str,
        ):
            return explicit_reason

        if data.get("done") is True:
            return "stop"

        return None


    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
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
                    "/api/chat",
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
                "Ollama model invocation failed."
            ) from exc

        error = data.get(
            "error"
        )

        if error:
            raise ModelProviderInvocationError(
                "Ollama returned an inference error."
            )

        message = data.get(
            "message"
        )

        if not isinstance(
            message,
            dict,
        ):
            raise ModelProviderContractError(
                "Ollama response did not contain "
                "a valid message object."
            )

        content = message.get(
            "content"
        )

        if not isinstance(
            content,
            str,
        ):
            raise ModelProviderContractError(
                "Ollama response message did not "
                "contain text content."
            )

        input_tokens = self._token_count(
            data.get(
                "prompt_eval_count"
            )
        )

        output_tokens = self._token_count(
            data.get(
                "eval_count"
            )
        )

        total_tokens: int | None = None

        if (
            input_tokens is not None
            and output_tokens is not None
        ):
            total_tokens = (
                input_tokens
                + output_tokens
            )

        return ModelResponse(
            text=content,
            provider_id=(
                self.descriptor.provider_id
            ),
            model=model_name,
            usage=ModelUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
            finish_reason=(
                self._finish_reason(
                    data
                )
            ),
            metadata={
                "local": True,
            },
        )


    def stream(
        self,
        request: ModelRequest,
    ) -> Iterator[ModelStreamChunk]:
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
                    "/api/chat",
                    json=payload,
                ) as response:

                    response.raise_for_status()

                    for line in response.iter_lines():
                        if not line:
                            continue

                        try:
                            data = json.loads(
                                line
                            )

                        except json.JSONDecodeError as exc:
                            raise ModelProviderContractError(
                                "Ollama stream returned "
                                "invalid JSON."
                            ) from exc

                        if data.get("error"):
                            raise ModelProviderInvocationError(
                                "Ollama returned a streaming "
                                "inference error."
                            )

                        message = data.get(
                            "message",
                            {},
                        )

                        if not isinstance(
                            message,
                            dict,
                        ):
                            raise ModelProviderContractError(
                                "Ollama stream returned "
                                "an invalid message."
                            )

                        content = message.get(
                            "content",
                            "",
                        )

                        if not isinstance(
                            content,
                            str,
                        ):
                            content = str(
                                content
                            )

                        done = (
                            data.get("done")
                            is True
                        )

                        if content or done:
                            yield ModelStreamChunk(
                                delta=content,
                                provider_id=(
                                    self.descriptor.provider_id
                                ),
                                model=model_name,
                                finish_reason=(
                                    self._finish_reason(
                                        data
                                    )
                                ),
                                metadata={
                                    "local": True,
                                },
                            )

        except (
            ModelProviderContractError,
            ModelProviderInvocationError,
        ):
            raise

        except httpx.HTTPError as exc:
            raise ModelProviderInvocationError(
                "Ollama streaming invocation failed."
            ) from exc


    def health(
        self,
    ) -> ModelHealth:
        started = time.perf_counter()

        try:
            with self._client() as client:
                response = client.get(
                    "/api/tags"
                )

                response.raise_for_status()

                data = response.json()

            latency_ms = (
                time.perf_counter()
                - started
            ) * 1000.0

            models = data.get(
                "models",
                [],
            )

            model_count = (
                len(models)
                if isinstance(models, list)
                else 0
            )

            return ModelHealth(
                provider_id=(
                    self.descriptor.provider_id
                ),
                status=(
                    ModelHealthStatus.healthy
                ),
                latency_ms=latency_ms,
                message="Ollama is reachable.",
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
                    "Ollama is not reachable."
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
            location=ProviderLocation.local,
            text_generation=True,
            streaming=True,
            json_mode=True,

            # Tool/vision capability can vary by model.
            # Do not over-advertise until W02-REG-05.
            tools=False,
            vision=False,

            # Embeddings will use a dedicated boundary later.
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

        return ModelCostEstimate(
            provider_id=(
                self.descriptor.provider_id
            ),
            model=model_name,
            local=True,

            # Local inference has no external model-provider fee.
            # Device compute is deliberately not represented here.
            estimated_provider_cost=Decimal(
                "0"
            ),

            currency="GBP",
            pricing_available=True,
            reason_codes=[
                "LOCAL_PROVIDER_NO_PROVIDER_FEE"
            ],
            metadata={
                "device_compute_not_included": True,
            },
        )