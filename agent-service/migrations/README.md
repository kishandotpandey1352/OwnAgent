# Phase 3 database migrations

`phase3_001_governance_automation.sql` establishes persistent tables for 3J audit and 3K workflow/idempotency/outbox/approval/DLQ state.

Production rules:

- Apply through a reviewed migration pipeline.
- Back up before destructive migrations.
- Use forward migration + rollback/data-backfill plan.
- Application roles must not receive UPDATE permission on `phase3_audit_events`.
- Tenant filtering is mandatory in every repository query; add database-level RLS matching your existing authentication model where applicable.
- Never store provider/API secrets in any table above.
