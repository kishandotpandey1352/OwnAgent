-- ============================================================
-- Phase 3G-C
-- Financial fact validation + normalization
-- ============================================================


alter table analysis_facts
add column if not exists
canonical_metric_key text;


alter table analysis_facts
add column if not exists
normalized_numeric_value numeric;


alter table analysis_facts
add column if not exists
normalization_multiplier numeric;


alter table analysis_facts
add column if not exists
validation_score double precision;


alter table analysis_facts
add column if not exists
validation_details jsonb
not null
default '{}'::jsonb;


alter table analysis_facts
add column if not exists
validated_at timestamptz;


-- ------------------------------------------------------------
-- Constraints
-- ------------------------------------------------------------

do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname =
            'analysis_facts_validation_score_check'
    ) then

        alter table analysis_facts
        add constraint
        analysis_facts_validation_score_check
        check (
            validation_score is null
            or (
                validation_score >= 0
                and validation_score <= 1
            )
        );

    end if;
end;
$$;


do $$
begin
    if not exists (
        select 1
        from pg_constraint
        where conname =
            'analysis_facts_normalization_multiplier_check'
    ) then

        alter table analysis_facts
        add constraint
        analysis_facts_normalization_multiplier_check
        check (
            normalization_multiplier is null
            or normalization_multiplier > 0
        );

    end if;
end;
$$;


-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------

create index if not exists
analysis_facts_canonical_metric_idx
on analysis_facts (
    user_id,
    canonical_metric_key
);


create index if not exists
analysis_facts_validated_document_idx
on analysis_facts (
    user_id,
    document_id,
    validation_status,
    canonical_metric_key
);