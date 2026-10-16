from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class FinancialFactChartSource(
    BaseModel,
):
    source_ledger_id: str

    document_id: str | None = None

    chunk_id: str | None = None

    source_title: str | None = None

    page_number: int | None = None

    source_snippet: str | None = None

    retrieval_score: float | None = None


class FinancialFactChartPoint(
    BaseModel,
):
    fact_id: str

    period_label: str

    period_start: date | None = None

    period_end: date | None = None

    value: float

    numeric_value: str

    normalized_numeric_value: (
        str | None
    ) = None

    raw_value: str | None = None

    validation_score: (
        float | None
    ) = None

    source: (
        FinancialFactChartSource
        | None
    ) = None


class FinancialFactChartResponse(
    BaseModel,
):
    ok: bool = True

    document_id: str

    metric_key: str

    metric_label: str

    value_type: str

    company: str | None = None

    category: str | None = None

    statement_type: str | None = None

    currency: str | None = None

    unit_label: str | None = None

    source_scales: list[str] = Field(
        default_factory=list,
    )

    chart_type: Literal[
        "line",
        "bar",
    ]

    x_axis_label: str = "Period"

    y_axis_label: str

    points: list[
        FinancialFactChartPoint
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )