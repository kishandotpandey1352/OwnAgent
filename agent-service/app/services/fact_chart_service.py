from __future__ import annotations

import re

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from supabase import (
    Client,
    create_client,
)

from app.core.config import settings

from app.schemas.fact_charts import (
    FinancialFactChartPoint,
    FinancialFactChartResponse,
    FinancialFactChartSource,
)


CHARTABLE_VALUE_TYPES = {
    "currency",
    "percentage",
    "number",
    "count",
    "ratio",
    "per_share",
}


class FactChartError(
    RuntimeError,
):
    pass


def _client() -> Client:
    if not settings.supabase_url:
        raise FactChartError(
            "SUPABASE_URL is required."
        )

    if not (
        settings
        .supabase_service_role_key
    ):
        raise FactChartError(
            "SUPABASE_SERVICE_ROLE_KEY "
            "is required."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


def _clean(
    value: Any,
) -> str | None:
    if value is None:
        return None

    value = " ".join(
        str(value)
        .strip()
        .split()
    )

    return value or None


def _decimal(
    value: Any,
) -> Decimal | None:
    if (
        value is None
        or value == ""
    ):
        return None

    try:
        return Decimal(
            str(value)
        )

    except Exception:
        return None


def _parse_date(
    value: Any,
) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(
            str(value)
        )

    except ValueError:
        return None


def _year_from_label(
    value: str | None,
) -> int | None:
    if not value:
        return None

    match = re.search(
        r"\b((?:19|20)\d{2})\b",
        value,
    )

    if not match:
        return None

    return int(
        match.group(1)
    )


def _period_identity(
    row: dict[str, Any],
) -> str | None:
    period_end = _clean(
        row.get(
            "period_end"
        )
    )

    if period_end:
        return (
            f"end:{period_end}"
        )

    period_start = _clean(
        row.get(
            "period_start"
        )
    )

    if period_start:
        return (
            f"start:{period_start}"
        )

    period_label = _clean(
        row.get(
            "period_label"
        )
    )

    if period_label:
        return (
            "label:"
            + period_label.lower()
        )

    return None


def _period_sort_key(
    row: dict[str, Any],
) -> tuple[int, int]:
    period_end = _parse_date(
        row.get(
            "period_end"
        )
    )

    if period_end:
        return (
            0,
            period_end.toordinal(),
        )

    period_start = _parse_date(
        row.get(
            "period_start"
        )
    )

    if period_start:
        return (
            0,
            period_start.toordinal(),
        )

    year = _year_from_label(
        _clean(
            row.get(
                "period_label"
            )
        )
    )

    if year:
        return (
            0,
            date(
                year,
                12,
                31,
            ).toordinal(),
        )

    return (
        1,
        0,
    )


def _load_validated_rows(
    *,
    client: Client,
    user_id: str,
    document_id: str,
) -> list[
    dict[str, Any]
]:
    response = (
        client
        .table(
            "analysis_facts"
        )
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
                "raw_value,"
                "unit_label,"
                "currency,"
                "scale,"
                "period_label,"
                "period_start,"
                "period_end,"
                "category,"
                "statement_type,"
                "validation_status,"
                "validation_score"
            )
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
        .eq(
            "validation_status",
            "validated",
        )
        .execute()
    )

    return (
        response.data
        or []
    )


def _load_sources(
    *,
    client: Client,
    user_id: str,
    source_ids: list[str],
) -> dict[
    str,
    dict[str, Any],
]:
    if not source_ids:
        return {}

    response = (
        client
        .table(
            "source_ledger"
        )
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

    return {
        str(
            row["id"]
        ): row
        for row
        in (
            response.data
            or []
        )
    }


def _same_optional(
    actual: Any,
    expected: str | None,
) -> bool:
    if expected is None:
        return True

    return (
        (_clean(actual) or "")
        .lower()
        ==
        expected.strip().lower()
    )


def _filter_metric_rows(
    *,
    rows: list[
        dict[str, Any]
    ],
    metric_key: str,
    company: str | None,
    category: str | None,
    statement_type: str | None,
) -> list[
    dict[str, Any]
]:
    selected = []

    for row in rows:
        row_metric_key = (
            _clean(
                row.get(
                    "metric_key"
                )
            )
        )

        canonical_key = (
            _clean(
                row.get(
                    "canonical_metric_key"
                )
            )
        )

        if metric_key not in {
            row_metric_key,
            canonical_key,
        }:
            continue

        if not _same_optional(
            row.get(
                "company"
            ),
            company,
        ):
            continue

        if not _same_optional(
            row.get(
                "category"
            ),
            category,
        ):
            continue

        if not _same_optional(
            row.get(
                "statement_type"
            ),
            statement_type,
        ):
            continue

        selected.append(
            row
        )

    return selected


def _check_context(
    rows: list[
        dict[str, Any]
    ],
) -> tuple[
    str | None,
    str | None,
    str | None,
]:
    contexts = {
        (
            _clean(
                row.get(
                    "company"
                )
            ),
            _clean(
                row.get(
                    "category"
                )
            ),
            _clean(
                row.get(
                    "statement_type"
                )
            ),
        )
        for row in rows
    }

    if len(contexts) > 1:
        readable = [
            {
                "company": company,
                "category": category,
                "statement_type":
                    statement_type,
            }
            for (
                company,
                category,
                statement_type,
            ) in sorted(
                contexts,
                key=lambda item: str(
                    item
                ),
            )
        ]

        raise FactChartError(
            (
                "This metric has multiple "
                "financial contexts. "
                "Specify company, category "
                "or statement_type before "
                "charting. Contexts: "
                f"{readable}"
            )
        )

    if not contexts:
        return (
            None,
            None,
            None,
        )

    return next(
        iter(
            contexts
        )
    )


def _dedupe_periods(
    rows: list[
        dict[str, Any]
    ],
) -> list[
    dict[str, Any]
]:
    by_period: dict[
        str,
        dict[str, Any],
    ] = {}

    for row in rows:
        period_key = (
            _period_identity(
                row
            )
        )

        if not period_key:
            continue

        value = (
            _decimal(
                row.get(
                    "normalized_numeric_value"
                )
            )
        )

        if value is None:
            value = (
                _decimal(
                    row.get(
                        "numeric_value"
                    )
                )
            )

        if value is None:
            continue

        existing = (
            by_period.get(
                period_key
            )
        )

        if existing is None:
            by_period[
                period_key
            ] = row

            continue

        existing_value = (
            _decimal(
                existing.get(
                    "normalized_numeric_value"
                )
            )
        )

        if existing_value is None:
            existing_value = (
                _decimal(
                    existing.get(
                        "numeric_value"
                    )
                )
            )

        if (
            existing_value
            is not None
            and existing_value
            != value
        ):
            raise FactChartError(
                (
                    "Multiple validated "
                    "values exist for the "
                    "same metric and period. "
                    "Charting was blocked "
                    "rather than guessing."
                )
            )

        existing_score = float(
            existing.get(
                "validation_score"
            )
            or 0.0
        )

        new_score = float(
            row.get(
                "validation_score"
            )
            or 0.0
        )

        if (
            new_score
            > existing_score
        ):
            by_period[
                period_key
            ] = row

    deduped = list(
        by_period.values()
    )

    deduped.sort(
        key=_period_sort_key
    )

    return deduped


def _y_axis_label(
    *,
    metric_label: str,
    value_type: str,
    currency: str | None,
    unit_label: str | None,
) -> str:
    if value_type == "percentage":
        return (
            f"{metric_label} (%)"
        )

    if currency:
        return (
            f"{metric_label} "
            f"({currency})"
        )

    if unit_label:
        return (
            f"{metric_label} "
            f"({unit_label})"
        )

    return (
        f"{metric_label} "
        "(normalized reported units)"
    )


def build_document_fact_chart(
    *,
    user_id: str,
    document_id: str,
    metric_key: str,
    chart_type: Literal[
        "auto",
        "line",
        "bar",
    ] = "auto",
    company: str | None = None,
    category: str | None = None,
    statement_type: (
        str | None
    ) = None,
) -> FinancialFactChartResponse:
    client = _client()

    all_rows = (
        _load_validated_rows(
            client=client,
            user_id=user_id,
            document_id=(
                document_id
            ),
        )
    )

    rows = (
        _filter_metric_rows(
            rows=all_rows,
            metric_key=metric_key,
            company=company,
            category=category,
            statement_type=(
                statement_type
            ),
        )
    )

    if not rows:
        raise FactChartError(
            (
                "No validated facts "
                "were found for metric "
                f"'{metric_key}'."
            )
        )

    value_types = {
        str(
            row.get(
                "value_type"
            )
            or ""
        )
        for row in rows
    }

    if len(
        value_types
    ) != 1:
        raise FactChartError(
            (
                "The selected metric has "
                "mixed value types and "
                "cannot be charted safely."
            )
        )

    value_type = next(
        iter(
            value_types
        )
    )

    if (
        value_type
        not in CHARTABLE_VALUE_TYPES
    ):
        raise FactChartError(
            (
                "The selected fact type "
                f"'{value_type}' is not "
                "numeric and cannot be "
                "charted."
            )
        )

    (
        resolved_company,
        resolved_category,
        resolved_statement_type,
    ) = _check_context(
        rows
    )

    warnings: list[str] = []

    missing_period_count = sum(
        1
        for row in rows
        if not _period_identity(
            row
        )
    )

    if missing_period_count:
        warnings.append(
            (
                f"{missing_period_count} "
                "validated fact(s) were "
                "excluded because their "
                "period could not be "
                "resolved."
            )
        )

    rows = [
        row
        for row in rows
        if _period_identity(
            row
        )
    ]

    rows = _dedupe_periods(
        rows
    )

    if not rows:
        raise FactChartError(
            (
                "Validated facts exist "
                "for this metric, but "
                "none has a resolved "
                "period suitable for "
                "charting."
            )
        )

    currencies = {
        value
        for value in (
            _clean(
                row.get(
                    "currency"
                )
            )
            for row in rows
        )
        if value
    }

    if len(currencies) > 1:
        raise FactChartError(
            (
                "The selected metric has "
                "multiple currencies and "
                "cannot be placed on one "
                "chart safely."
            )
        )

    currency = (
        next(
            iter(
                currencies
            )
        )
        if currencies
        else None
    )

    unit_labels = {
        value
        for value in (
            _clean(
                row.get(
                    "unit_label"
                )
            )
            for row in rows
        )
        if value
    }

    if len(unit_labels) > 1:
        raise FactChartError(
            (
                "The selected metric has "
                "multiple unit labels and "
                "cannot be placed on one "
                "chart safely."
            )
        )

    unit_label = (
        next(
            iter(
                unit_labels
            )
        )
        if unit_labels
        else None
    )

    source_scales = sorted(
        {
            value
            for value in (
                _clean(
                    row.get(
                        "scale"
                    )
                )
                for row in rows
            )
            if value
        }
    )

    metric_label = (
        _clean(
            rows[0].get(
                "metric_label"
            )
        )
        or metric_key
    )

    source_ids = list(
        {
            str(
                row[
                    "source_ledger_id"
                ]
            )
            for row in rows
            if row.get(
                "source_ledger_id"
            )
        }
    )

    source_map = (
        _load_sources(
            client=client,
            user_id=user_id,
            source_ids=source_ids,
        )
    )

    points: list[
        FinancialFactChartPoint
    ] = []

    for row in rows:
        normalized = (
            _decimal(
                row.get(
                    "normalized_numeric_value"
                )
            )
        )

        numeric = (
            _decimal(
                row.get(
                    "numeric_value"
                )
            )
        )

        chart_value = (
            normalized
            if normalized is not None
            else numeric
        )

        if chart_value is None:
            continue

        source_id = (
            _clean(
                row.get(
                    "source_ledger_id"
                )
            )
        )

        source = None

        if source_id:
            source_row = (
                source_map.get(
                    source_id
                )
            )

            if source_row:
                source = (
                    FinancialFactChartSource(
                        source_ledger_id=(
                            source_id
                        ),
                        document_id=(
                            _clean(
                                source_row.get(
                                    "document_id"
                                )
                            )
                        ),
                        chunk_id=(
                            _clean(
                                source_row.get(
                                    "chunk_id"
                                )
                            )
                        ),
                        source_title=(
                            _clean(
                                source_row.get(
                                    "source_title"
                                )
                            )
                        ),
                        page_number=(
                            source_row.get(
                                "page_number"
                            )
                        ),
                        source_snippet=(
                            _clean(
                                source_row.get(
                                    "source_snippet"
                                )
                            )
                        ),
                        retrieval_score=(
                            float(
                                source_row[
                                    "retrieval_score"
                                ]
                            )
                            if source_row.get(
                                "retrieval_score"
                            )
                            is not None
                            else None
                        ),
                    )
                )

        period_label = (
            _clean(
                row.get(
                    "period_label"
                )
            )
            or _clean(
                row.get(
                    "period_end"
                )
            )
            or _clean(
                row.get(
                    "period_start"
                )
            )
            or "Period"
        )

        points.append(
            FinancialFactChartPoint(
                fact_id=str(
                    row["id"]
                ),
                period_label=(
                    period_label
                ),
                period_start=(
                    row.get(
                        "period_start"
                    )
                ),
                period_end=(
                    row.get(
                        "period_end"
                    )
                ),
                value=float(
                    chart_value
                ),
                numeric_value=str(
                    numeric
                    if numeric
                    is not None
                    else chart_value
                ),
                normalized_numeric_value=(
                    str(
                        normalized
                    )
                    if normalized
                    is not None
                    else None
                ),
                raw_value=(
                    _clean(
                        row.get(
                            "raw_value"
                        )
                    )
                ),
                validation_score=(
                    float(
                        row[
                            "validation_score"
                        ]
                    )
                    if row.get(
                        "validation_score"
                    )
                    is not None
                    else None
                ),
                source=source,
            )
        )

    if not points:
        raise FactChartError(
            "No numeric chart points remained."
        )

    resolved_chart_type: Literal[
        "line",
        "bar",
    ]

    if chart_type == "auto":
        resolved_chart_type = (
            "line"
            if len(points) >= 3
            else "bar"
        )

    elif chart_type == "line":
        resolved_chart_type = (
            "line"
        )

    else:
        resolved_chart_type = (
            "bar"
        )

    return (
        FinancialFactChartResponse(
            document_id=document_id,
            metric_key=metric_key,
            metric_label=metric_label,
            value_type=value_type,
            company=resolved_company,
            category=resolved_category,
            statement_type=(
                resolved_statement_type
            ),
            currency=currency,
            unit_label=unit_label,
            source_scales=(
                source_scales
            ),
            chart_type=(
                resolved_chart_type
            ),
            y_axis_label=(
                _y_axis_label(
                    metric_label=(
                        metric_label
                    ),
                    value_type=(
                        value_type
                    ),
                    currency=currency,
                    unit_label=(
                        unit_label
                    ),
                )
            ),
            points=points,
            warnings=warnings,
        )
    )