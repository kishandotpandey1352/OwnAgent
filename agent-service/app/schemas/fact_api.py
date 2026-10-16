from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class FinancialFactSourceView(BaseModel):
    source_ledger_id: str

    document_id: str | None = None

    chunk_id: str | None = None

    source_title: str | None = None

    page_number: int | None = None

    source_snippet: str | None = None

    retrieval_score: float | None = None


class FinancialFactView(BaseModel):
    fact_id: str

    document_id: str

    company: str | None = None

    metric_key: str

    canonical_metric_key: str | None = None

    metric_label: str

    value_type: str

    numeric_value: str | None = None

    normalized_numeric_value: str | None = None

    text_value: str | None = None

    raw_value: str | None = None

    unit_key: str | None = None

    unit_label: str | None = None

    currency: str | None = None

    scale: str | None = None

    period_label: str | None = None

    period_start: date | None = None

    period_end: date | None = None

    category: str | None = None

    statement_type: str | None = None

    validation_status: str

    validation_score: float | None = None

    validation_reason: str | None = None

    validation_details: dict = Field(
        default_factory=dict,
    )

    source: FinancialFactSourceView | None = None


class FinancialFactStatusSummary(BaseModel):
    total: int = 0

    pending: int = 0

    validated: int = 0

    rejected: int = 0

    conflict: int = 0


class DocumentFinancialFactsResponse(BaseModel):
    ok: bool = True

    document_id: str

    status_filter: str

    total: int

    offset: int

    limit: int

    summary: FinancialFactStatusSummary

    facts: list[FinancialFactView] = Field(
        default_factory=list,
    )