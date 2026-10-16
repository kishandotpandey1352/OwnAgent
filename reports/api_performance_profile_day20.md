# Day 18 API Performance Profiling Report

## Goal

The goal of Day 18 was to add the `/risk-analysis` endpoint and profile the performance of all three finance API endpoints.

## Profiling Setup

| Item | Value |
|---|---|
| Base URL | `http://localhost:8000` |
| Requests per endpoint | 10 |
| Concurrency | 2 |
| Backend | FastAPI connected to vLLM |
| Served model | `finance-qwen1.5b` |

## Endpoint Performance

| Endpoint | Successful | Failed | Requests/sec | Mean Latency (s) | P50 (s) | P95 (s) | Total Tokens/sec | Completion Tokens/sec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| /summarize | 10 | 0 | 2.445 | 0.804 | 0.626 | 1.150 | 339.576 | 102.435 |
| /qa | 10 | 0 | 2.176 | 0.916 | 0.850 | 1.261 | 378.620 | 119.679 |
| /risk-analysis | 10 | 0 | 0.583 | 3.429 | 3.394 | 4.320 | 202.908 | 111.949 |

## Interpretation

The profiling results compare the behavior of the summarization, financial QA, and risk-analysis endpoints under the same request count and concurrency level. Differences in latency are expected because each endpoint uses a different prompt structure and may generate different numbers of tokens.

The `/risk-analysis` endpoint usually has a longer structured prompt and may generate a longer response, so it can have higher latency than shorter summarization or QA requests.

## Day 18 Status

Day 18 is complete when the `/risk-analysis` endpoint returns structured risk analysis and the profiling report is generated successfully.
