-- ============================================================
-- Phase 3G-A
-- Financial Facts + Source Ledger
--
-- Metrics and units are intentionally dynamic.
-- Only bounded system concepts use CHECK constraints.
-- ============================================================


-- ------------------------------------------------------------
-- SOURCE LEDGER
-- ------------------------------------------------------------

create table if not exists source_ledger (
    id text primary key,

    user_id text not null,

    source_type text not null,

    source_id text not null,

    document_id text,

    chunk_id text,

    source_title text,

    source_uri text,

    page_number integer,

    source_snippet text not null,

    retrieval_score double precision,

    source_fingerprint text not null,

    metadata jsonb
        not null
        default '{}'::jsonb,

    created_at timestamptz
        not null
        default now(),

    constraint source_ledger_source_type_check
        check (
            source_type in (
                'document',
                'dataset',
                'web'
            )
        ),

    constraint source_ledger_page_number_check
        check (
            page_number is null
            or page_number >= 1
        ),

    constraint source_ledger_retrieval_score_check
        check (
            retrieval_score is null
            or (
                retrieval_score >= 0
                and retrieval_score <= 1
            )
        ),

    constraint source_ledger_document_source_check
        check (
            source_type <> 'document'
            or document_id is not null
        ),

    constraint source_ledger_user_fingerprint_unique
        unique (
            user_id,
            source_fingerprint
        )
);


create index if not exists
source_ledger_user_idx
on source_ledger (
    user_id
);


create index if not exists
source_ledger_document_idx
on source_ledger (
    user_id,
    document_id
);


create index if not exists
source_ledger_chunk_idx
on source_ledger (
    user_id,
    chunk_id
);


create index if not exists
source_ledger_source_idx
on source_ledger (
    user_id,
    source_type,
    source_id
);


-- ------------------------------------------------------------
-- ANALYSIS FACTS
-- ------------------------------------------------------------

create table if not exists analysis_facts (
    id text primary key,

    user_id text not null,

    document_id text,

    company text,

    metric_key text not null,

    metric_label text not null,

    value_type text not null,

    numeric_value numeric,

    text_value text,

    raw_value text not null,

    unit_key text,

    unit_label text,

    currency text,

    scale text,

    period_label text,

    period_start date,

    period_end date,

    category text,

    statement_type text,

    source_ledger_id text not null
        references source_ledger(id)
        on delete cascade,

    confidence double precision
        not null,

    extraction_method text
        not null
        default 'llm_structured_extraction',

    validation_status text
        not null
        default 'pending',

    validation_reason text,

    attributes jsonb
        not null
        default '{}'::jsonb,

    fact_fingerprint text not null,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now(),

    constraint analysis_facts_value_type_check
        check (
            value_type in (
                'currency',
                'percentage',
                'number',
                'count',
                'ratio',
                'per_share',
                'text'
            )
        ),

    constraint analysis_facts_confidence_check
        check (
            confidence >= 0
            and confidence <= 1
        ),

    constraint analysis_facts_validation_status_check
        check (
            validation_status in (
                'pending',
                'validated',
                'rejected',
                'conflict'
            )
        ),

    constraint analysis_facts_period_check
        check (
            period_start is null
            or period_end is null
            or period_start <= period_end
        ),

    constraint analysis_facts_value_presence_check
        check (
            numeric_value is not null
            or text_value is not null
        ),

    constraint analysis_facts_user_fingerprint_unique
        unique (
            user_id,
            fact_fingerprint
        )
);


create index if not exists
analysis_facts_user_idx
on analysis_facts (
    user_id
);


create index if not exists
analysis_facts_document_idx
on analysis_facts (
    user_id,
    document_id
);


create index if not exists
analysis_facts_metric_idx
on analysis_facts (
    user_id,
    metric_key
);


create index if not exists
analysis_facts_company_metric_idx
on analysis_facts (
    user_id,
    company,
    metric_key
);


create index if not exists
analysis_facts_period_idx
on analysis_facts (
    user_id,
    period_start,
    period_end
);


create index if not exists
analysis_facts_validation_idx
on analysis_facts (
    user_id,
    validation_status
);


create index if not exists
analysis_facts_source_ledger_idx
on analysis_facts (
    source_ledger_id
);


-- ------------------------------------------------------------
-- UPDATED_AT
-- ------------------------------------------------------------

create or replace function set_analysis_fact_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;


drop trigger if exists
analysis_facts_set_updated_at
on analysis_facts;


create trigger analysis_facts_set_updated_at
before update
on analysis_facts
for each row
execute function set_analysis_fact_updated_at();


-- ------------------------------------------------------------
-- SECURITY
--
-- These tables are intended to be accessed server-side using
-- the Supabase service-role key.
-- ------------------------------------------------------------

alter table source_ledger
enable row level security;


alter table analysis_facts
enable row level security;