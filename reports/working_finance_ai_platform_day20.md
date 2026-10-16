# Working Finance AI Platform

## Goal

The goal of Week 4 was to turn the finance fine-tuning project into a local production-style AI platform.

## Final Local Architecture

```text
User / API Client
  ↓
FastAPI service
  ↓
vLLM OpenAI-compatible backend
  ↓
finance-qwen1.5b local serving model
  ↓
Prometheus metrics collection
  ↓
Grafana dashboard visualization