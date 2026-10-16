# Phase 3 AWS deployment model

Production deployment should separate the synchronous API from long-running agent/automation workers.

Recommended target:

- CloudFront/WAF -> frontend
- API Gateway or ALB -> stateless FastAPI API on ECS Fargate
- SQS -> agent/automation workers on ECS Fargate (or EKS/AgentCore if platform requirements justify it)
- Aurora PostgreSQL/pgvector -> relational/RAG data
- DynamoDB -> workflow state and idempotency where low-latency key access is useful
- S3 -> uploaded documents, raw evidence artifacts and evaluation datasets
- ElastiCache -> non-authoritative cache/rate-limit data
- Secrets Manager + KMS -> secrets/encryption
- CloudWatch + OpenTelemetry -> logs, metrics and traces
- EventBridge -> event routing/schedules; SQS remains the work queue

## Scaling

Workers must be stateless. Scale from queue depth / age-of-oldest-message, with hard concurrency caps so provider quotas are not overwhelmed. Keep workflow state external. SQS is at-least-once, so all actions must be idempotent.

## Security

Use separate IAM task roles for API, document workers, web workers and automation workers. Do not grant the LLM credentials. Put DB/Redis/workers in private subnets. Restrict outbound egress for agents that do not need public network access.

## Rollout

Keep `multi_agent_enabled`, `compliance_blocking_enabled`, and `automation_enabled` behind feature flags. Roll out development -> staging -> internal users -> canary -> wider traffic.
