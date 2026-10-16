from prometheus_client import Counter, Histogram


INFERENCE_REQUESTS_TOTAL = Counter(
    "finance_llm_inference_requests_total",
    "Total number of inference requests.",
    ["route", "status"],
)

INFERENCE_LATENCY_SECONDS = Histogram(
    "finance_llm_inference_latency_seconds",
    "Inference request latency in seconds.",
    ["route"],
)
