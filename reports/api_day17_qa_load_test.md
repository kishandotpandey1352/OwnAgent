# Day 17 QA Endpoint and Load Test Report

## Goal

The goal of Day 17 was to add a financial question-answering endpoint and run load tests against the FastAPI service connected to the vLLM backend.

## Endpoint Added

```text
POST /qa

Request Schema::

{
  "question": "Why did operating margin decline?",
  "context": "Financial context text",
  "max_tokens": 128,
  "temperature": 0.2
}



Response Schema::
{
  "task": "financial_qa",
  "answer": "Generated answer",
  "model": "finance-qwen1.5b",
  "latency_seconds": 1.23,
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 40,
    "total_tokens": 140
  }
}

