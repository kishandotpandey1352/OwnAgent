# Day 18 Risk Analysis Endpoint Report

## Goal

The goal of Day 18 was to add a finance risk-analysis endpoint and profile API performance across the main FastAPI endpoints.

## Endpoint Added

```text
POST /risk-analysis

Request Schema::
{
  "text": "Financial text to analyze for risk",
  "max_tokens": 192,
  "temperature": 0.2
}

Response Schema::

{
  "task": "risk_analysis",
  "risk_analysis": "Generated structured risk analysis",
  "model": "finance-qwen1.5b",
  "latency_seconds": 1.23,
  "usage": {
    "prompt_tokens": 120,
    "completion_tokens": 80,
    "total_tokens": 200
  }
}