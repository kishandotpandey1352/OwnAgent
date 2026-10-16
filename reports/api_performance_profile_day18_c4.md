# Day 18 API Performance Profiling Report

## Goal

The goal of Day 18 was to add the `/risk-analysis` endpoint and profile the performance of all three finance API endpoints.

## Profiling Setup

| Item | Value |
|---|---|
| Base URL | `http://localhost:8000` |
| Requests per endpoint | 20 |
| Concurrency | 4 |
| Backend | FastAPI connected to vLLM |
| Served model | `finance-qwen1.5b` |

## Endpoint Performance

| Endpoint | Successful | Failed | Requests/sec | Mean Latency (s) | P50 (s) | P95 (s) | Total Tokens/sec | Completion Tokens/sec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| /summarize | 20 | 0 | 5.689 | 0.670 | 0.662 | 0.810 | 755.484 | 203.662 |
| /qa | 20 | 0 | 3.914 | 0.994 | 0.904 | 1.360 | 690.557 | 213.096 |
| /risk-analysis | 20 | 0 | 1.346 | 2.971 | 2.961 | 3.190 | 468.442 | 258.451 |

## Interpretation

The profiling results compare the behavior of the summarization, financial QA, and risk-analysis endpoints under the same request count and concurrency level. Differences in latency are expected because each endpoint uses a different prompt structure and may generate different numbers of tokens.

The `/risk-analysis` endpoint usually has a longer structured prompt and may generate a longer response, so it can have higher latency than shorter summarization or QA requests.

## Day 18 Status

Day 18 is complete when the `/risk-analysis` endpoint returns structured risk analysis and the profiling report is generated successfully.
