-- Phase 3J/3K governance + automation persistence foundation.
-- Apply through the project's migration mechanism; do not manually mutate prod.

create table if not exists phase3_audit_events (
    event_id text primary key,
    request_id text not null,
    tenant_id text,
    user_id text,
    trace_id text,
    plan_id text,
    task_id text,
    event_type text not null,
    event_timestamp timestamptz not null,
    actor_type text not null,
    actor_id text not null,
    severity text not null,
    metadata jsonb not null default '{}'::jsonb,
    previous_event_hash text,
    event_hash text not null,
    created_at timestamptz not null default now()
);
create index if not exists idx_phase3_audit_request on phase3_audit_events (tenant_id, request_id, event_timestamp);
create index if not exists idx_phase3_audit_trace on phase3_audit_events (tenant_id, trace_id, event_timestamp);

-- Audit rows are append-only. Retention/deletion should be performed only by a
-- dedicated compliance/retention role; application roles should not receive UPDATE.
create or replace function phase3_prevent_audit_update() returns trigger language plpgsql as $$
begin
    raise exception 'phase3_audit_events is append-only';
end;
$$;
drop trigger if exists trg_phase3_audit_no_update on phase3_audit_events;
create trigger trg_phase3_audit_no_update
before update on phase3_audit_events
for each row execute function phase3_prevent_audit_update();

create table if not exists phase3_workflows (
    workflow_id text primary key,
    event_id text not null,
    tenant_id text not null,
    state text not null,
    attempts integer not null default 0 check (attempts >= 0),
    last_error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
create index if not exists idx_phase3_workflow_tenant_state on phase3_workflows (tenant_id, state, updated_at desc);

create table if not exists phase3_idempotency (
    tenant_id text not null,
    idempotency_key text not null,
    status text not null,
    result jsonb,
    error text,
    first_seen timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (tenant_id, idempotency_key)
);

create table if not exists phase3_automation_outbox (
    outbox_id text primary key,
    tenant_id text not null,
    event_id text not null,
    event_type text not null,
    event_payload jsonb not null,
    status text not null default 'pending',
    attempts integer not null default 0,
    last_error text,
    created_at timestamptz not null default now(),
    published_at timestamptz
);
create index if not exists idx_phase3_outbox_pending on phase3_automation_outbox (status, created_at) where status = 'pending';

create table if not exists phase3_approvals (
    approval_id text primary key,
    workflow_id text not null,
    tenant_id text not null,
    requested_by text not null,
    action text not null,
    original_payload jsonb not null,
    decision text not null default 'pending',
    decided_by text,
    requested_at timestamptz not null default now(),
    decided_at timestamptz,
    check (decision in ('pending', 'approved', 'rejected'))
);
create index if not exists idx_phase3_approvals_pending on phase3_approvals (tenant_id, decision, requested_at desc);

create table if not exists phase3_dead_letters (
    dlq_id text primary key,
    tenant_id text not null,
    event_id text not null,
    workflow_id text,
    event_payload jsonb not null,
    error_category text not null,
    attempt_count integer not null check (attempt_count > 0),
    first_failure_at timestamptz not null,
    last_failure_at timestamptz not null,
    trace_id text,
    status text not null default 'open',
    created_at timestamptz not null default now()
);
create index if not exists idx_phase3_dlq_open on phase3_dead_letters (tenant_id, status, last_failure_at desc);
