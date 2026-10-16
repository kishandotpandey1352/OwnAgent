-- =========================================================
-- Phase 3H-D
-- Web provenance support for source_ledger
-- =========================================================
--
-- Existing document/fact source rows remain unchanged.
--
-- Web evidence is persisted into the same generic
-- source_ledger with source_type = 'web'.
-- =========================================================


alter table public.source_ledger
    add column if not exists source_url text;


alter table public.source_ledger
    add column if not exists source_domain text;


alter table public.source_ledger
    add column if not exists retrieved_at timestamptz;


alter table public.source_ledger
    add column if not exists trust_tier text;


alter table public.source_ledger
    add column if not exists provider text;


alter table public.source_ledger
    add column if not exists content_type text;


alter table public.source_ledger
    add column if not exists page_number integer;


-- ---------------------------------------------------------
-- Helpful indexes
-- ---------------------------------------------------------

create index if not exists
source_ledger_user_source_type_idx
on public.source_ledger (
    user_id,
    source_type
);


create index if not exists
source_ledger_source_domain_idx
on public.source_ledger (
    source_domain
)
where source_domain is not null;


create index if not exists
source_ledger_retrieved_at_idx
on public.source_ledger (
    retrieved_at desc
)
where retrieved_at is not null;


-- ---------------------------------------------------------
-- Data constraints
-- ---------------------------------------------------------

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname =
            'source_ledger_trust_tier_check'
    ) then
        alter table public.source_ledger
        add constraint
            source_ledger_trust_tier_check
        check (
            trust_tier is null
            or trust_tier in (
                'public_authority',
                'trusted_domain',
                'finance_candidate',
                'general_web',
                'low_trust'
            )
        );
    end if;
end
$$;


do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname =
            'source_ledger_provider_check'
    ) then
        alter table public.source_ledger
        add constraint
            source_ledger_provider_check
        check (
            provider is null
            or provider in (
                'serper',
                'document',
                'dataset'
            )
        );
    end if;
end
$$;