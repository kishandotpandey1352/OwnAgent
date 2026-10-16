from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    Field,
    model_validator,
)


class FactSourceType(
    str,
    Enum,
):
    """
    Intentionally small/bounded.

    The source type describes WHERE evidence
    came from, not what financial metric it is.
    """

    document = "document"
    dataset = "dataset"
    web = "web"


class FactValueType(
    str,
    Enum,
):
    """
    Generic machine-level representation.

    Metric names and units remain dynamic.
    """

    currency = "currency"
    percentage = "percentage"
    number = "number"
    count = "count"
    ratio = "ratio"
    per_share = "per_share"
    text = "text"


class FactValidationStatus(
    str,
    Enum,
):
    """
    3G-B will initially create pending facts.

    3G-C will move them to validated,
    rejected, or conflict.
    """

    pending = "pending"
    validated = "validated"
    rejected = "rejected"
    conflict = "conflict"


class SourceLedgerCreate(
    BaseModel,
):
    """
    Evidence supporting one or more facts.

    This is intentionally source-generic so the
    same ledger can later support document,
    dataset, and web evidence.
    """

    source_type: FactSourceType

    source_id: str = Field(
        min_length=1,
        max_length=500,
    )

    document_id: str | None = Field(
        default=None,
        max_length=500,
    )

    chunk_id: str | None = Field(
        default=None,
        max_length=500,
    )

    source_title: str | None = Field(
        default=None,
        max_length=1000,
    )

    source_uri: str | None = Field(
        default=None,
        max_length=4000,
    )

    page_number: int | None = Field(
        default=None,
        ge=1,
    )

    source_snippet: str = Field(
        min_length=1,
        max_length=8000,
    )

    retrieval_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(
        mode="after",
    )
    def validate_document_source(
        self,
    ) -> "SourceLedgerCreate":
        if (
            self.source_type
            == FactSourceType.document
            and not self.document_id
        ):
            raise ValueError(
                "document_id is required "
                "for document evidence."
            )

        return self


class SourceLedgerEntry(
    SourceLedgerCreate,
):
    id: str

    user_id: str

    source_fingerprint: str

    created_at: datetime


class FinancialFactCandidate(
    BaseModel,
):
    """
    Dynamic/document-agnostic fact produced
    by an extractor.

    We deliberately do NOT enumerate metrics
    such as revenue, EBITDA, ARR, occupancy,
    subscribers, production volume, etc.
    """

    company: str | None = Field(
        default=None,
        max_length=500,
    )

    metric_key: str = Field(
        min_length=1,
        max_length=300,
    )

    metric_label: str = Field(
        min_length=1,
        max_length=500,
    )

    value_type: FactValueType

    numeric_value: Decimal | None = None

    text_value: str | None = Field(
        default=None,
        max_length=8000,
    )

    raw_value: str = Field(
        default=None,
        max_length=2000,
    )

    unit_key: str | None = Field(
        default=None,
        max_length=200,
    )

    unit_label: str | None = Field(
        default=None,
        max_length=300,
    )

    currency: str | None = Field(
        default=None,
        max_length=20,
    )

    scale: str | None = Field(
        default=None,
        max_length=100,
    )

    period_label: str | None = Field(
        default=None,
        max_length=300,
    )

    period_start: date | None = None

    period_end: date | None = None

    category: str | None = Field(
        default=None,
        max_length=300,
    )

    statement_type: str | None = Field(
        default=None,
        max_length=300,
    )

    document_id: str | None = Field(
        default=None,
        max_length=500,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    extraction_method: str = Field(
        default="llm_structured_extraction",
        max_length=200,
    )

    attributes: dict[str, Any] = Field(
        default_factory=dict,
    )

    @model_validator(
        mode="after",
    )
    def validate_value_shape(
        self,
    ) -> "FinancialFactCandidate":
        if (
            self.value_type
            == FactValueType.text
        ):
            if not (
                self.text_value
                and self.text_value.strip()
            ):
                raise ValueError(
                    "text_value is required "
                    "when value_type is text."
                )

            return self

        if self.numeric_value is None:
            raise ValueError(
                "numeric_value is required "
                "for non-text financial facts."
            )

        return self

    @model_validator(
        mode="after",
    )
    def validate_period(
        self,
    ) -> "FinancialFactCandidate":
        if (
            self.period_start
            and self.period_end
            and self.period_start
            > self.period_end
        ):
            raise ValueError(
                "period_start cannot be "
                "after period_end."
            )

        return self


class FinancialFactCreate(
    FinancialFactCandidate,
):
    source_ledger_id: str = Field(
        min_length=1,
        max_length=500,
    )


class FinancialFact(
    FinancialFactCreate,
):
    id: str

    user_id: str

    fact_fingerprint: str

    validation_status: (
        FactValidationStatus
    )

    validation_reason: (
        str | None
    ) = None

    canonical_metric_key: (
        str | None
    ) = None

    normalized_numeric_value: (
        Decimal | None
    ) = None

    normalization_multiplier: (
        Decimal | None
    ) = None

    validation_score: (
        float | None
    ) = None

    validation_details: dict[
        str,
        Any,
    ] = Field(
        default_factory=dict,
    )

    validated_at: (
        datetime | None
    ) = None

    created_at: datetime

    updated_at: datetime


class FinancialFactBundleCreate(
    BaseModel,
):
    source: SourceLedgerCreate

    fact: FinancialFactCandidate


class FinancialFactBundle(
    BaseModel,
):
    fact: FinancialFact

    source: SourceLedgerEntry


class FinancialFactWithSource(
    BaseModel,
):
    fact: FinancialFact

    source: SourceLedgerEntry


class FinancialFactListResponse(
    BaseModel,
):
    ok: bool = True

    document_id: str

    fact_count: int

    facts: list[
        FinancialFactWithSource
    ] = Field(
        default_factory=list,
    )


class FactValidationUpdate(
    BaseModel,
):
    status: FactValidationStatus

    reason: str | None = Field(
        default=None,
        max_length=4000,
    )

# ---------------------------------------------------------
# Phase 3G-B
# Financial fact extraction
# ---------------------------------------------------------


class ExtractedFinancialFactDraft(
    BaseModel,
):
    """
    Raw structured output produced by the LLM.

    document_id and extraction_method are deliberately
    NOT supplied by the model. The application assigns
    those values itself.
    """

    source_number: int = Field(
        ge=1,
    )

    company: str | None = Field(
        default=None,
        max_length=500,
    )

    metric_key: str = Field(
        min_length=1,
        max_length=300,
    )

    metric_label: str = Field(
        min_length=1,
        max_length=500,
    )

    value_type: FactValueType

    numeric_value: Decimal | None = None

    text_value: str | None = Field(
        default=None,
        max_length=8000,
    )

    raw_value: str = Field(
        default=None,
        max_length=2000,
    )

    unit_key: str | None = Field(
        default=None,
        max_length=200,
    )

    unit_label: str | None = Field(
        default=None,
        max_length=300,
    )

    currency: str | None = Field(
        default=None,
        max_length=20,
    )

    scale: str | None = Field(
        default=None,
        max_length=100,
    )

    period_label: str | None = Field(
        default=None,
        max_length=300,
    )

    category: str | None = Field(
        default=None,
        max_length=300,
    )

    statement_type: str | None = Field(
        default=None,
        max_length=300,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    attributes: dict[str, Any] = Field(
        default_factory=dict,
    )


class ExtractedFinancialFactBatch(
    BaseModel,
):
    facts: list[
        ExtractedFinancialFactDraft
    ] = Field(
        default_factory=list,
    )

    notes: list[str] = Field(
        default_factory=list,
    )


class FinancialFactExtractionRequest(
    BaseModel,
):
    document_id: str = Field(
        min_length=1,
        max_length=500,
    )

    company_hint: str | None = Field(
        default=None,
        max_length=500,
    )

    requested_metrics: list[str] = Field(
        default_factory=list,
    )

    focus_queries: list[str] = Field(
        default_factory=list,
    )

    top_k_per_query: int = Field(
        default=6,
        ge=1,
        le=20,
    )

    max_sources: int = Field(
        default=24,
        ge=1,
        le=40,
    )

    max_facts: int = Field(
        default=100,
        ge=1,
        le=200,
    )

    include_text_facts: bool = False

    persist: bool = True


class FinancialFactExtractionResult(
    BaseModel,
):
    ok: bool = True

    document_id: str

    file_name: str

    model: str

    retrieval_queries: list[str] = Field(
        default_factory=list,
    )

    retrieved_source_count: int = 0

    best_retrieval_score: float = 0.0

    candidate_count: int = 0

    persisted_count: int = 0

    skipped_count: int = 0

    candidates: list[
        FinancialFactCandidate
    ] = Field(
        default_factory=list,
    )

    saved_facts: list[
        FinancialFactBundle
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )

# ---------------------------------------------------------
# Phase 3G-C
# Fact validation / normalization
# ---------------------------------------------------------


class FinancialFactValidationResult(
    BaseModel,
):
    fact_id: str

    metric_key: str

    canonical_metric_key: str

    status: FactValidationStatus

    validation_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    reason: str

    normalized_numeric_value: (
        Decimal | None
    ) = None

    normalization_multiplier: (
        Decimal | None
    ) = None

    currency: str | None = None

    scale: str | None = None

    period_start: date | None = None

    period_end: date | None = None

    warnings: list[str] = Field(
        default_factory=list,
    )


class FinancialFactValidationResponse(
    BaseModel,
):
    ok: bool = True

    document_id: str

    processed_count: int = 0

    validated_count: int = 0

    rejected_count: int = 0

    conflict_count: int = 0

    results: list[
        FinancialFactValidationResult
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )