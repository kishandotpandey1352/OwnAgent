# Day 13 Inference Benchmark Comparison

## Goal

The goal of Day 13 was to compare vLLM serving performance under different generation lengths and concurrency levels.

## Serving Setup

| Item | Value |
|---|---|
| Serving engine | vLLM |
| API format | OpenAI-compatible API |
| Served model | `finance-qwen1.5b` |
| Base model | `Qwen/Qwen2.5-1.5B-Instruct` |
| Endpoint | `http://localhost:8001/v1/chat/completions` |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |
| VRAM | ~8GB |

## Latency Comparison

| Run | Max Tokens | Requests | Mean Latency (s) | P50 Latency (s) | P95 Latency (s) | Min (s) | Max (s) |
|---|---:|---:|---:|---:|---:|---:|---:|
| t64 | 64 | 10 | 0.574 | 0.469 | 0.851 | 0.417 | 0.947 |
| t128 | 128 | 10 | 0.467 | 0.476 | 0.524 | 0.401 | 0.541 |
| t256 | 256 | 10 | 0.543 | 0.441 | 0.693 | 0.416 | 0.974 |

## Throughput Comparison

| Run | Concurrency | Requests | Total Time (s) | Requests/sec | Total Tokens/sec | Completion Tokens/sec |
|---|---:|---:|---:|---:|---:|---:|
| c1 | 1 | 20 | 26.137 | 0.765 | 104.373 | 66.113 |
| c2 | 2 | 20 | 14.659 | 1.364 | 186.435 | 118.219 |
| c4 | 4 | 20 | 8.665 | 2.308 | 314.957 | 199.546 |

## Interpretation

The latency benchmark shows how response time changes as the maximum generation length increases. Higher `max_tokens` usually increases latency because the model may generate more tokens.

The throughput benchmark shows how vLLM handles concurrent requests. Increasing concurrency can improve overall requests/sec and tokens/sec, but it may also increase individual request latency if the GPU becomes saturated.

These results create a serving baseline for the finance AI platform and will be used later when comparing different serving backends, quantization settings, or model sizes.
