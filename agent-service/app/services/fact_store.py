from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from decimal import Decimal
from functools import lru_cache
from typing import Any
from uuid import uuid4

from supabase import (
    Client,
    create_client,
)

from app.core.config import settings
from app.schemas.facts import (
    FactValidationStatus,
    FinancialFact,
    FinancialFactBundle,
    FinancialFactBundleCreate,
    FinancialFactCandidate,
    FinancialFactCreate,
    FinancialFactWithSource,
    SourceLedgerCreate,
    SourceLedgerEntry,
)


class FactStoreError(
    RuntimeError,
):
    pass


class FactNotFoundError(
    FactStoreError,
):
    pass


class FactAccessError(
    FactStoreError,
):
    pass


def _clean_string(
    value: str | None,
) -> str:
    if not value:
        return ""

    return " ".join(
        value
        .strip()
        .lower()
        .split()
    )


def _serialize_fingerprint_value(
    value: Any,
) -> Any:
    if isinstance(
        value,
        Decimal,
    ):
        return format(
            value,
            "f",
        )

    if isinstance(
        value,
        date,
    ):
        return value.isoformat()

    if isinstance(
        value,
        dict,
    ):
        return {
            str(key):
                _serialize_fingerprint_value(
                    item,
                )
            for key, item
            in sorted(
                value.items(),
                key=lambda pair:
                    str(pair[0]),
            )
        }

    if isinstance(
        value,
        (list, tuple),
    ):
        return [
            _serialize_fingerprint_value(
                item,
            )
            for item in value
        ]

    return value


def _sha256(
    payload: dict[str, Any],
) -> str:
    serialized = json.dumps(
        _serialize_fingerprint_value(
            payload,
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )

    return hashlib.sha256(
        serialized.encode(
            "utf-8",
        )
    ).hexdigest()


def _settings_value(
    name: str,
) -> str | None:
    """
    Prefer existing pydantic Settings fields.

    Fall back to process environment so this
    service works even if config.py has not
    explicitly declared the Supabase fields.
    """

    value = getattr(
        settings,
        name,
        None,
    )

    if (
        isinstance(
            value,
            str,
        )
        and value.strip()
    ):
        return value.strip()

    environment_name = (
        name.upper()
    )

    fallback = os.getenv(
        environment_name
    )

    if (
        fallback
        and fallback.strip()
    ):
        return fallback.strip()

    return None


@lru_cache(
    maxsize=1,
)
def _get_supabase_client() -> Client:
    url = _settings_value(
        "supabase_url"
    )

    service_role_key = (
        _settings_value(
            "supabase_service_role_key"
        )
    )

    if not url:
        raise FactStoreError(
            "SUPABASE_URL is required "
            "for financial fact storage."
        )

    if not service_role_key:
        raise FactStoreError(
            "SUPABASE_SERVICE_ROLE_KEY "
            "is required for financial "
            "fact storage."
        )

    return create_client(
        url,
        service_role_key,
    )


def _source_fingerprint(
    source: SourceLedgerCreate,
) -> str:
    """
    A source fingerprint identifies the same
    evidence snippet if extraction is rerun.

    Retrieval score is intentionally excluded,
    because the same evidence can be retrieved
    at a different similarity score later.
    """

    return _sha256(
        {
            "source_type":
                source
                .source_type
                .value,

            "source_id":
                _clean_string(
                    source.source_id
                ),

            "document_id":
                _clean_string(
                    source.document_id
                ),

            "chunk_id":
                _clean_string(
                    source.chunk_id
                ),

            "page_number":
                source.page_number,

            "source_snippet":
                _clean_string(
                    source.source_snippet
                ),
        }
    )


def _fact_fingerprint(
    *,
    source_ledger_id: str,
    fact: FinancialFactCandidate,
) -> str:
    """
    Prevents duplicate fact rows when the same
    document is extracted repeatedly.

    We include the source ledger ID because two
    different pieces of evidence may legitimately
    state the same metric/value.
    """

    return _sha256(
        {
            "source_ledger_id":
                source_ledger_id,

            "document_id":
                _clean_string(
                    fact.document_id
                ),

            "company":
                _clean_string(
                    fact.company
                ),

            "metric_key":
                _clean_string(
                    fact.metric_key
                ),

            "value_type":
                fact
                .value_type
                .value,

            "numeric_value":
                fact.numeric_value,

            "text_value":
                _clean_string(
                    fact.text_value
                ),

            "raw_value":
                _clean_string(
                    fact.raw_value
                ),

            "unit_key":
                _clean_string(
                    fact.unit_key
                ),

            "currency":
                _clean_string(
                    fact.currency
                ),

            "scale":
                _clean_string(
                    fact.scale
                ),

            "period_label":
                _clean_string(
                    fact.period_label
                ),

            "period_start":
                fact.period_start,

            "period_end":
                fact.period_end,
        }
    )


def _source_from_row(
    row: dict[str, Any],
) -> SourceLedgerEntry:
    return (
        SourceLedgerEntry
        .model_validate(
            row
        )
    )


def _fact_from_row(
    row: dict[str, Any],
) -> FinancialFact:
    return (
        FinancialFact
        .model_validate(
            row
        )
    )


def _first_row(
    response: Any,
) -> dict[str, Any] | None:
    rows = (
        getattr(
            response,
            "data",
            None,
        )
        or []
    )

    if not rows:
        return None

    return rows[0]


def get_or_create_source_entry(
    *,
    user_id: str,
    source: SourceLedgerCreate,
) -> SourceLedgerEntry:
    client = (
        _get_supabase_client()
    )

    fingerprint = (
        _source_fingerprint(
            source
        )
    )

    existing_response = (
        client
        .table(
            "source_ledger"
        )
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "source_fingerprint",
            fingerprint,
        )
        .limit(1)
        .execute()
    )

    existing = _first_row(
        existing_response
    )

    if existing:
        return _source_from_row(
            existing
        )

    source_id = (
        f"source-{uuid4()}"
    )

    payload = (
        source.model_dump(
            mode="json",
            exclude_none=True,
        )
    )

    payload.update(
        {
            "id":
                source_id,

            "user_id":
                user_id,

            "source_fingerprint":
                fingerprint,
        }
    )

    try:
        response = (
            client
            .table(
                "source_ledger"
            )
            .insert(
                payload
            )
            .execute()
        )

    except Exception as error:
        """
        A concurrent extraction may have inserted
        the identical fingerprint after our first
        SELECT. Re-read before failing.
        """

        retry_response = (
            client
            .table(
                "source_ledger"
            )
            .select("*")
            .eq(
                "user_id",
                user_id,
            )
            .eq(
                "source_fingerprint",
                fingerprint,
            )
            .limit(1)
            .execute()
        )

        retry = _first_row(
            retry_response
        )

        if retry:
            return _source_from_row(
                retry
            )

        raise FactStoreError(
            "Failed to create "
            "source ledger entry."
        ) from error

    row = _first_row(
        response
    )

    if not row:
        raise FactStoreError(
            "Source ledger insert "
            "returned no row."
        )

    return _source_from_row(
        row
    )


def get_source_entry(
    *,
    user_id: str,
    source_ledger_id: str,
) -> SourceLedgerEntry:
    client = (
        _get_supabase_client()
    )

    response = (
        client
        .table(
            "source_ledger"
        )
        .select("*")
        .eq(
            "id",
            source_ledger_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    row = _first_row(
        response
    )

    if not row:
        raise FactNotFoundError(
            "Source ledger entry "
            "was not found."
        )

    return _source_from_row(
        row
    )


def get_or_create_financial_fact(
    *,
    user_id: str,
    fact: FinancialFactCreate,
) -> FinancialFact:
    client = (
        _get_supabase_client()
    )

    candidate = (
        FinancialFactCandidate(
            **fact.model_dump(
                exclude={
                    "source_ledger_id"
                }
            )
        )
    )

    fingerprint = (
        _fact_fingerprint(
            source_ledger_id=(
                fact.source_ledger_id
            ),
            fact=candidate,
        )
    )

    existing_response = (
        client
        .table(
            "analysis_facts"
        )
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "fact_fingerprint",
            fingerprint,
        )
        .limit(1)
        .execute()
    )

    existing = _first_row(
        existing_response
    )

    if existing:
        return _fact_from_row(
            existing
        )

    fact_id = (
        f"fact-{uuid4()}"
    )

    payload = (
        fact.model_dump(
            mode="json",
            exclude_none=True,
        )
    )

    payload.update(
        {
            "id":
                fact_id,

            "user_id":
                user_id,

            "fact_fingerprint":
                fingerprint,

            "validation_status":
                (
                    FactValidationStatus
                    .pending
                    .value
                ),
        }
    )

    try:
        response = (
            client
            .table(
                "analysis_facts"
            )
            .insert(
                payload
            )
            .execute()
        )

    except Exception as error:
        retry_response = (
            client
            .table(
                "analysis_facts"
            )
            .select("*")
            .eq(
                "user_id",
                user_id,
            )
            .eq(
                "fact_fingerprint",
                fingerprint,
            )
            .limit(1)
            .execute()
        )

        retry = _first_row(
            retry_response
        )

        if retry:
            return _fact_from_row(
                retry
            )

        raise FactStoreError(
            "Failed to create "
            "financial fact."
        ) from error

    row = _first_row(
        response
    )

    if not row:
        raise FactStoreError(
            "Financial fact insert "
            "returned no row."
        )

    return _fact_from_row(
        row
    )


def create_fact_bundle(
    *,
    user_id: str,
    bundle: FinancialFactBundleCreate,
) -> FinancialFactBundle:
    """
    Save provenance first, then save the fact.

    The source entry is deduplicated, so multiple
    facts can safely reference the same evidence.
    """

    source = (
        get_or_create_source_entry(
            user_id=user_id,
            source=bundle.source,
        )
    )

    fact_document_id = (
        bundle.fact.document_id
        or source.document_id
    )

    if (
        bundle.fact.document_id
        and source.document_id
        and bundle.fact.document_id
        != source.document_id
    ):
        raise FactStoreError(
            "Fact document_id does not "
            "match source document_id."
        )

    candidate = (
        bundle.fact.model_copy(
            update={
                "document_id":
                    fact_document_id,
            }
        )
    )

    fact_input = (
        FinancialFactCreate(
            **candidate.model_dump(),
            source_ledger_id=(
                source.id
            ),
        )
    )

    fact = (
        get_or_create_financial_fact(
            user_id=user_id,
            fact=fact_input,
        )
    )

    return FinancialFactBundle(
        fact=fact,
        source=source,
    )


def get_financial_fact(
    *,
    user_id: str,
    fact_id: str,
) -> FinancialFactWithSource:
    client = (
        _get_supabase_client()
    )

    response = (
        client
        .table(
            "analysis_facts"
        )
        .select("*")
        .eq(
            "id",
            fact_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .limit(1)
        .execute()
    )

    row = _first_row(
        response
    )

    if not row:
        raise FactNotFoundError(
            "Financial fact "
            "was not found."
        )

    fact = _fact_from_row(
        row
    )

    source = get_source_entry(
        user_id=user_id,
        source_ledger_id=(
            fact.source_ledger_id
        ),
    )

    return (
        FinancialFactWithSource(
            fact=fact,
            source=source,
        )
    )


def list_document_facts(
    *,
    user_id: str,
    document_id: str,
    include_rejected: bool = False,
) -> list[
    FinancialFactWithSource
]:
    client = (
        _get_supabase_client()
    )

    query = (
        client
        .table(
            "analysis_facts"
        )
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
    )

    if not include_rejected:
        query = query.neq(
            "validation_status",
            (
                FactValidationStatus
                .rejected
                .value
            ),
        )

    response = (
        query
        .order(
            "created_at"
        )
        .execute()
    )

    fact_rows = (
        response.data
        or []
    )

    if not fact_rows:
        return []

    facts = [
        _fact_from_row(
            row
        )
        for row in fact_rows
    ]

    source_ids = list(
        {
            fact.source_ledger_id
            for fact in facts
        }
    )

    source_response = (
        client
        .table(
            "source_ledger"
        )
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .in_(
            "id",
            source_ids,
        )
        .execute()
    )

    source_map = {
        row["id"]:
            _source_from_row(
                row
            )
        for row
        in (
            source_response.data
            or []
        )
    }

    results: list[
        FinancialFactWithSource
    ] = []

    for fact in facts:
        source = source_map.get(
            fact.source_ledger_id
        )

        if not source:
            continue

        results.append(
            FinancialFactWithSource(
                fact=fact,
                source=source,
            )
        )

    return results


def update_fact_validation(
    *,
    user_id: str,
    fact_id: str,
    status: FactValidationStatus,
    reason: str | None = None,
) -> FinancialFact:
    """
    3G-C will use this.

    Adding it now prevents us from redesigning
    storage when validation is implemented.
    """

    client = (
        _get_supabase_client()
    )

    payload: dict[str, Any] = {
        "validation_status":
            status.value,

        "validation_reason":
            reason,
    }

    response = (
        client
        .table(
            "analysis_facts"
        )
        .update(
            payload
        )
        .eq(
            "id",
            fact_id,
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

    row = _first_row(
        response
    )

    if not row:
        raise FactNotFoundError(
            "Financial fact "
            "was not found."
        )

    return _fact_from_row(
        row
    )


def delete_document_facts(
    *,
    user_id: str,
    document_id: str,
) -> int:
    """
    Cleanup helper.

    Later this can be called when a document is
    removed from document memory.
    """

    client = (
        _get_supabase_client()
    )

    facts_response = (
        client
        .table(
            "analysis_facts"
        )
        .select(
            "id,source_ledger_id"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
        .execute()
    )

    rows = (
        facts_response.data
        or []
    )

    if not rows:
        return 0

    source_ids = list(
        {
            row[
                "source_ledger_id"
            ]
            for row in rows
            if row.get(
                "source_ledger_id"
            )
        }
    )

    (
        client
        .table(
            "analysis_facts"
        )
        .delete()
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
        .execute()
    )

    if source_ids:
        (
            client
            .table(
                "source_ledger"
            )
            .delete()
            .eq(
                "user_id",
                user_id,
            )
            .in_(
                "id",
                source_ids,
            )
            .execute()
        )

    return len(rows)