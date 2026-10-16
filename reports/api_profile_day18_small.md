# Day 18 API Performance Profiling Report

## Goal

The goal of Day 18 was to add the `/risk-analysis` endpoint and profile the performance of all three finance API endpoints.

## Profiling Setup

| Item | Value |
|---|---|
| Base URL | `http://localhost:8000` |
| Requests per endpoint | 3 |
| Concurrency | 1 |
| Backend | FastAPI connected to vLLM |
| Served model | `finance-qwen1.5b` |

## Endpoint Performance

| Endpoint | Successful | Failed | Requests/sec | Mean Latency (s) | P50 (s) | P95 (s) | Total Tokens/sec | Completion Tokens/sec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| /summarize | 3 | 0 | 1.662 | 0.601 | 0.614 | 0.614 | 223.323 | 62.065 |
| /qa | 3 | 0 | 1.319 | 0.758 | 0.751 | 0.751 | 235.683 | 74.750 |
| /risk-analysis | 3 | 0 | 0.400 | 2.500 | 2.495 | 2.495 | 139.208 | 76.804 |

## Interpretation

The profiling results compare the behavior of the summarization, financial QA, and risk-analysis endpoints under the same request count and concurrency level. Differences in latency are expected because each endpoint uses a different prompt structure and may generate different numbers of tokens.

The `/risk-analysis` endpoint usually has a longer structured prompt and may generate a longer response, so it can have higher latency than shorter summarization or QA requests.

## Day 18 Status

Day 18 is complete when the `/risk-analysis` endpoint returns structured risk analysis and the profiling report is generated successfully.
