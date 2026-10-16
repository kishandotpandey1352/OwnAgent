# Day 20 End-to-End Test Report

## Goal

The goal of Day 20 was to validate the complete local production-style Finance AI Platform from API request to model response and monitoring.

## Overall Status

```text
PASSED
```

## Service Checks

| Check | Status | HTTP Status | Latency (s) |
|---|---|---:|---:|
| fastapi_health | PASS | 200 | 0.027 |
| fastapi_metrics | PASS | 200 | 0.039 |
| vllm_models | PASS | 200 | 0.027 |
| prometheus_ready | PASS | 200 | 0.019 |

## Endpoint Tests

| Endpoint | Status | HTTP Status | Latency (s) | Model | Total Tokens |
|---|---|---:|---:|---|---:|
| /summarize | PASS | 200 | 0.892 | finance-qwen1.5b | 136 |
| /qa | PASS | 200 | 0.995 | finance-qwen1.5b | 171 |
| /risk-analysis | PASS | 200 | 2.655 | finance-qwen1.5b | 349 |

## Endpoint Output Previews

### /summarize

```text
The company's revenue grew by 18% due to increased enterprise demand. Despite this, operating expenses surged with higher cloud infrastructure costs and employee compensation, leading to potential continued margin pressures.
```

### /qa

```text
Operating margin declined because despite an increase in revenue (due to stronger enterprise demand), there was also an increase in operating expenses (higher cloud infrastructure costs and employee compensation). This led to a decrease in profit relative to sales, resulting in a lower operating mar
```

### /risk-analysis

```text
1. **Key Risks**
   - Revenue Risk: Increased revenue is not enough if it comes at the expense of declining margins.
   - Margin Risk: Declining gross margin indicates reduced profitability per unit sold.
   - Cash Flow Risk: Higher operating expenses could lead to cash flow pressures unless managed
```

## Validated Architecture

```text
User / API Client
  ↓
FastAPI service
  ↓
vLLM backend
  ↓
finance-qwen1.5b
  ↓
Prometheus metrics
  ↓
Grafana dashboard
```

## Conclusion

The end-to-end test passed. The Finance AI Platform successfully handled summarization, financial QA, and risk-analysis requests through FastAPI, routed them to the vLLM backend, returned model responses, and exposed monitoring metrics for Prometheus/Grafana.
