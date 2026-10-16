from fastapi import FastAPI, Depends
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from src.api.auth import verify_api_key
from src.api.metrics import (
    INFERENCE_REQUESTS_TOTAL,
    INFERENCE_LATENCY_SECONDS,
)
from src.api.schemas import (
    SummarizeRequest,
    QARequest,
    RiskAnalysisRequest,
    InferenceResponse,
)
from src.inference.loader import get_finance_llm


app = FastAPI(
    title="Finance LLM Inference API",
    version="0.1.0",
    description="Secure FastAPI service for finance-domain LLM inference.",
)


@app.get("/health")
def health():
    model = get_finance_llm()
    return {
        "status": "ok",
        "service": "finance-llm-inference-api",
        "model_id": model.model_id,
    }


@app.get("/ready")
def ready():
    model = get_finance_llm()
    return {
        "ready": model.model_loaded and model.adapter_loaded,
        "model_loaded": model.model_loaded,
        "adapter_loaded": model.adapter_loaded,
        "model_id": model.model_id,
    }


@app.post("/summarize", response_model=InferenceResponse)
def summarize(
    request: SummarizeRequest,
    _: None = Depends(verify_api_key),
):
    route = "summarize"

    with INFERENCE_LATENCY_SECONDS.labels(route=route).time():
        try:
            model = get_finance_llm()
            prompt = (
                "Summarize the following financial text clearly and concisely.\n\n"
                f"Text:\n{request.text}\n\nSummary:"
            )
            output = model.generate(
                prompt=prompt,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
            )

            INFERENCE_REQUESTS_TOTAL.labels(route=route, status="success").inc()

            return InferenceResponse(
                model_id=model.model_id,
                output=output,
            )
        except Exception as exc:
            INFERENCE_REQUESTS_TOTAL.labels(route=route, status="error").inc()
            raise RuntimeError(f"Summarization failed: {exc}") from exc


@app.post("/qa", response_model=InferenceResponse)
def qa(
    request: QARequest,
    _: None = Depends(verify_api_key),
):
    route = "qa"

    with INFERENCE_LATENCY_SECONDS.labels(route=route).time():
        try:
            model = get_finance_llm()
            prompt = (
                "Answer the financial question using only the provided context.\n\n"
                f"Context:\n{request.context}\n\n"
                f"Question:\n{request.question}\n\nAnswer:"
            )
            output = model.generate(
                prompt=prompt,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
            )

            INFERENCE_REQUESTS_TOTAL.labels(route=route, status="success").inc()

            return InferenceResponse(
                model_id=model.model_id,
                output=output,
            )
        except Exception as exc:
            INFERENCE_REQUESTS_TOTAL.labels(route=route, status="error").inc()
            raise RuntimeError(f"QA failed: {exc}") from exc


@app.post("/risk-analysis", response_model=InferenceResponse)
def risk_analysis(
    request: RiskAnalysisRequest,
    _: None = Depends(verify_api_key),
):
    route = "risk-analysis"

    with INFERENCE_LATENCY_SECONDS.labels(route=route).time():
        try:
            model = get_finance_llm()
            prompt = (
                "Identify the key financial risks in the following text. "
                "Return a concise risk analysis.\n\n"
                f"Text:\n{request.text}\n\nRisk analysis:"
            )
            output = model.generate(
                prompt=prompt,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
            )

            INFERENCE_REQUESTS_TOTAL.labels(route=route, status="success").inc()

            return InferenceResponse(
                model_id=model.model_id,
                output=output,
            )
        except Exception as exc:
            INFERENCE_REQUESTS_TOTAL.labels(route=route, status="error").inc()
            raise RuntimeError(f"Risk analysis failed: {exc}") from exc


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
