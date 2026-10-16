from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from app.core.config import settings
from app.schemas.fact_api import (
    DocumentFinancialFactsResponse,
    FinancialFactSourceView,
    FinancialFactStatusSummary,
    FinancialFactView,
)


VALID_STATUSES = {
    "all",
    "pending",
    "validated",
    "rejected",
    "conflict",
}


class FactQueryError(RuntimeError):
    pass


def _client() -> Client:
    if not settings.supabase_url:
        raise FactQueryError(
            "SUPABASE_URL is required."
        )

    if not settings.supabase_service_role_key:
        raise FactQueryError(
            "SUPABASE_SERVICE_ROLE_KEY is required."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def _string_or_none(
    value: Any,
) -> str | None:
    if value is None:
        return None

    value = str(value).strip()

    return value or None


def _numeric_string(
    value: Any,
) -> str | None:
    if value is None:
        return None

    return str(value)


def _load_status_summary(
    *,
    client: Client,
    user_id: str,
    document_id: str,
) -> FinancialFactStatusSummary:
    response = (
        client
        .table("analysis_facts")
        .select("validation_status")
        .eq("user_id", user_id)
        .eq("document_id", document_id)
        .execute()
    )

    summary = FinancialFactStatusSummary()

    for row in response.data or []:
        status = str(
            row.get(
                "validation_status",
                "",
            )
        )

        summary.total += 1

        if status == "pending":
            summary.pending += 1

        elif status == "validated":
            summary.validated += 1

        elif status == "rejected":
            summary.rejected += 1

        elif status == "conflict":
            summary.conflict += 1

    return summary


def _load_fact_rows(
    *,
    client: Client,
    user_id: str,
    document_id: str,
    status: str,
    offset: int,
    limit: int,
) -> list[dict[str, Any]]:
    query = (
        client
        .table("analysis_facts")
        .select(
            (
                "id,"
                "document_id,"
                "source_ledger_id,"
                "company,"
                "metric_key,"
                "canonical_metric_key,"
                "metric_label,"
                "value_type,"
                "numeric_value,"
                "normalized_numeric_value,"
                "text_value,"
                "raw_value,"
                "unit_key,"
                "unit_label,"
                "currency,"
                "scale,"
                "period_label,"
                "period_start,"
                "period_end,"
                "category,"
                "statement_type,"
                "validation_status,"
                "validation_score,"
                "validation_reason,"
                "validation_details,"
                "created_at"
            )
        )
        .eq("user_id", user_id)
        .eq("document_id", document_id)
    )

    if status != "all":
        query = query.eq(
            "validation_status",
            status,
        )

    response = (
        query
        .order(
            "validation_score",
            desc=True,
        )
        .range(
            offset,
            offset + limit - 1,
        )
        .execute()
    )

    return response.data or []


def _load_sources(
    *,
    client: Client,
    user_id: str,
    source_ids: list[str],
) -> dict[str, dict[str, Any]]:
    if not source_ids:
        return {}

    response = (
        client
        .table("source_ledger")
        .select(
            (
                "id,"
                "document_id,"
                "chunk_id,"
                "source_title,"
                "page_number,"
                "source_snippet,"
                "retrieval_score"
            )
        )
        .eq("user_id", user_id)
        .in_("id", source_ids)
        .execute()
    )

    return {
        str(row["id"]): row
        for row in response.data or []
    }


def _status_total(
    *,
    status: str,
    summary: FinancialFactStatusSummary,
) -> int:
    if status == "all":
        return summary.total

    if status == "pending":
        return summary.pending

    if status == "validated":
        return summary.validated

    if status == "rejected":
        return summary.rejected

    if status == "conflict":
        return summary.conflict

    return 0


def list_document_facts(
    *,
    user_id: str,
    document_id: str,
    status: str = "validated",
    offset: int = 0,
    limit: int = 100,
) -> DocumentFinancialFactsResponse:
    status = status.lower().strip()

    if status not in VALID_STATUSES:
        raise FactQueryError(
            f"Unsupported fact status: {status}"
        )

    client = _client()

    summary = _load_status_summary(
        client=client,
        user_id=user_id,
        document_id=document_id,
    )

    rows = _load_fact_rows(
        client=client,
        user_id=user_id,
        document_id=document_id,
        status=status,
        offset=offset,
        limit=limit,
    )

    source_ids = list(
        {
            str(row["source_ledger_id"])
            for row in rows
            if row.get("source_ledger_id")
        }
    )

    source_map = _load_sources(
        client=client,
        user_id=user_id,
        source_ids=source_ids,
    )

    facts: list[FinancialFactView] = []

    for row in rows:
        source_id = _string_or_none(
            row.get("source_ledger_id")
        )

        source_row = (
            source_map.get(source_id)
            if source_id
            else None
        )

        source = None

        if source_row and source_id:
            source = FinancialFactSourceView(
                source_ledger_id=source_id,
                document_id=_string_or_none(
                    source_row.get("document_id")
                ),
                chunk_id=_string_or_none(
                    source_row.get("chunk_id")
                ),
                source_title=_string_or_none(
                    source_row.get("source_title")
                ),
                page_number=source_row.get(
                    "page_number"
                ),
                source_snippet=_string_or_none(
                    source_row.get("source_snippet")
                ),
                retrieval_score=(
                    float(
                        source_row["retrieval_score"]
                    )
                    if source_row.get(
                        "retrieval_score"
                    )
                    is not None
                    else None
                ),
            )

        facts.append(
            FinancialFactView(
                fact_id=str(row["id"]),
                document_id=str(
                    row["document_id"]
                ),
                company=_string_or_none(
                    row.get("company")
                ),
                metric_key=str(
                    row.get("metric_key") or ""
                ),
                canonical_metric_key=(
                    _string_or_none(
                        row.get(
                            "canonical_metric_key"
                        )
                    )
                ),
                metric_label=str(
                    row.get("metric_label") or ""
                ),
                value_type=str(
                    row.get("value_type") or ""
                ),
                numeric_value=_numeric_string(
                    row.get("numeric_value")
                ),
                normalized_numeric_value=(
                    _numeric_string(
                        row.get(
                            "normalized_numeric_value"
                        )
                    )
                ),
                text_value=_string_or_none(
                    row.get("text_value")
                ),
                raw_value=_string_or_none(
                    row.get("raw_value")
                ),
                unit_key=_string_or_none(
                    row.get("unit_key")
                ),
                unit_label=_string_or_none(
                    row.get("unit_label")
                ),
                currency=_string_or_none(
                    row.get("currency")
                ),
                scale=_string_or_none(
                    row.get("scale")
                ),
                period_label=_string_or_none(
                    row.get("period_label")
                ),
                period_start=row.get(
                    "period_start"
                ),
                period_end=row.get(
                    "period_end"
                ),
                category=_string_or_none(
                    row.get("category")
                ),
                statement_type=_string_or_none(
                    row.get("statement_type")
                ),
                validation_status=str(
                    row.get(
                        "validation_status"
                    )
                    or "pending"
                ),
                validation_score=(
                    float(
                        row["validation_score"]
                    )
                    if row.get(
                        "validation_score"
                    )
                    is not None
                    else None
                ),
                validation_reason=(
                    _string_or_none(
                        row.get(
                            "validation_reason"
                        )
                    )
                ),
                validation_details=(
                    row.get(
                        "validation_details"
                    )
                    or {}
                ),
                source=source,
            )
        )

    return DocumentFinancialFactsResponse(
        document_id=document_id,
        status_filter=status,
        total=_status_total(
            status=status,
            summary=summary,
        ),
        offset=offset,
        limit=limit,
        summary=summary,
        facts=facts,
    )