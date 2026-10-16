from __future__ import annotations

from typing import Literal

from pydantic import (
    BaseModel,
    Field,
)

from datetime import date
from decimal import Decimal

from app.schemas.facts import (
    FactValidationStatus,
    FactValueType,
)


WebTrustTier = Literal[
    "public_authority",
    "trusted_domain",
    "finance_candidate",
    "general_web",
    "low_trust",
]


WebContentKind = Literal[
    "html",
    "text",
    "pdf",
]


class WebGapDecision(BaseModel):
    needs_web: bool = False

    reason: str | None = None

    requested_years: list[int] = Field(
        default_factory=list,
    )

    covered_years: list[int] = Field(
        default_factory=list,
    )

    missing_years: list[int] = Field(
        default_factory=list,
    )

    local_fact_count: int = 0

    local_source_count: int = 0


class WebResearchInput(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=4000,
    )

    gap_reason: str | None = Field(
        default=None,
        max_length=2000,
    )

    trusted_domains: list[str] = Field(
        default_factory=list,
        max_length=25,
    )

    max_results: int = Field(
        default=8,
        ge=1,
        le=20,
    )

    extract_structured_facts: bool = False


class WebSearchCandidate(BaseModel):
    rank: int = Field(
        ge=1,
    )

    original_position: int | None = None

    title: str

    url: str

    domain: str

    snippet: str | None = None

    trust_tier: WebTrustTier

    ranking_score: float


class WebEvidencePassage(BaseModel):
    text: str

    score: float

    page_number: int | None = None

    matched_terms: list[str] = Field(
        default_factory=list,
    )


class WebFetchedSource(BaseModel):
    search_rank: int

    title: str

    requested_url: str

    final_url: str

    domain: str

    content_type: WebContentKind

    trust_tier: WebTrustTier

    http_status: int

    text_chars: int = 0

    evidence_passages: list[
        WebEvidencePassage
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )


class WebFetchFailure(BaseModel):
    search_rank: int

    title: str

    url: str

    reason: str


# =========================================================
# Phase 3H-D
# Persistent citation source
# =========================================================


class WebCitationSource(BaseModel):
    # Citation number is request-scoped.
    #
    # Database source IDs are persistent.
    #
    # Example:
    #
    # [Web Source 2001]
    #
    source_number: int = Field(
        ge=2001,
    )

    source_id: str

    source_type: Literal[
        "web"
    ] = "web"

    title: str

    url: str

    domain: str

    snippet: str

    page_number: int | None = None

    trust_tier: WebTrustTier

    provider: Literal[
        "serper"
    ] = "serper"

    content_type: WebContentKind

    evidence_score: float | None = None

    retrieved_at: str

# =========================================================
# Phase 3H-E
# Structured web financial facts
# =========================================================


class WebFactExtractionResult(
    BaseModel
):
    attempted: bool = False

    model: str | None = None

    candidate_count: int = 0

    persisted_count: int = 0

    skipped_count: int = 0

    fact_ids: list[str] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )


class WebFactValidationResult(
    BaseModel
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

    warnings: list[str] = Field(
        default_factory=list,
    )


class WebFactValidationResponse(
    BaseModel
):
    ok: bool = True

    processed_count: int = 0

    validated_count: int = 0

    rejected_count: int = 0

    conflict_count: int = 0

    results: list[
        WebFactValidationResult
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )


class WebValidatedFinancialFact(
    BaseModel
):
    fact_id: str

    source_number: int = Field(
        ge=2001,
    )

    source_ledger_id: str

    company: str | None = None

    metric_key: str

    canonical_metric_key: str

    metric_label: str

    value_type: FactValueType

    numeric_value: Decimal | None = None

    normalized_numeric_value: (
        Decimal | None
    ) = None

    text_value: str | None = None

    raw_value: str

    unit_key: str | None = None

    unit_label: str | None = None

    currency: str | None = None

    scale: str | None = None

    period_label: str | None = None

    period_start: date | None = None

    period_end: date | None = None

    category: str | None = None

    statement_type: str | None = None

    validation_score: float = Field(
        ge=0.0,
        le=1.0,
    )

class WebResearchOutput(BaseModel):
    ok: bool = True

    provider: Literal[
        "serper"
    ] = "serper"

    query: str

    searched: bool = True

    candidate_count: int = 0

    candidates: list[
        WebSearchCandidate
    ] = Field(
        default_factory=list,
    )

    fetched_source_count: int = 0

    evidence_source_count: int = 0

    evidence_ready: bool = False

    fetched_sources: list[
        WebFetchedSource
    ] = Field(
        default_factory=list,
    )

    fetch_failures: list[
        WebFetchFailure
    ] = Field(
        default_factory=list,
    )

    # -----------------------------------------------------
    # Phase 3H-D
    # -----------------------------------------------------

    citation_ready: bool = False

    citation_source_count: int = 0

    citation_sources: list[
        WebCitationSource
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )

    extract_structured_facts: bool = False

    # -----------------------------------------------------
    # Phase 3H-E
    # -----------------------------------------------------

    structured_fact_attempted: bool = False

    structured_fact_ready: bool = False

    structured_fact_candidate_count: int = 0

    structured_fact_persisted_count: int = 0

    structured_fact_validated_count: int = 0

    structured_fact_rejected_count: int = 0

    structured_fact_conflict_count: int = 0

    validated_facts: list[WebValidatedFinancialFact] = Field(default_factory=list,)


    # -----------------------------------------------------
    # Phase 3H-F-C
    # Internal operational cache metadata
    # -----------------------------------------------------

    search_cache_hit: bool = False

    fetch_cache_hit: bool = False


# =========================================================
# Phase 3H-F-A
# Product-safe web research response
# =========================================================


class WebPublicCitation(
    BaseModel
):
    """
    Browser-safe representation of one persisted,
    citation-ready web evidence passage.

    Does not expose:
    - Serper ranking internals
    - raw fetch responses
    - fetch failures
    - provider payloads
    """

    source_number: int = Field(
        ge=2001,
    )

    source_id: str

    title: str

    url: str

    domain: str

    snippet: str

    page_number: int | None = None

    trust_tier: WebTrustTier

    content_type: WebContentKind

    retrieved_at: str


class WebPublicFinancialFact(
    BaseModel
):
    """
    Browser-safe representation of a deterministically
    validated structured web financial fact.
    """

    fact_id: str

    source_number: int = Field(
        ge=2001,
    )

    source_ledger_id: str

    company: str | None = None

    metric_key: str

    canonical_metric_key: str

    metric_label: str

    value_type: FactValueType

    raw_value: str

    numeric_value: Decimal | None = None

    normalized_numeric_value: (
        Decimal | None
    ) = None

    currency: str | None = None

    scale: str | None = None

    unit_label: str | None = None

    period_label: str | None = None

    validation_score: float = Field(
        ge=0.0,
        le=1.0,
    )


class WebProductResearchSummary(
    BaseModel
):
    """
    Narrow public contract returned by /agents/analyze.

    This is intentionally different from WebResearchOutput.

    WebResearchOutput is an INTERNAL tool result.

    WebProductResearchSummary is safe for the browser.
    """

    used: bool = False

    available: bool = False

    reason: str | None = None

    searched: bool = False

    evidence_ready: bool = False

    citation_ready: bool = False

    structured_fact_ready: bool = False

    citation_count: int = Field(
        default=0,
        ge=0,
    )

    validated_fact_count: int = Field(
        default=0,
        ge=0,
    )

    citations: list[
        WebPublicCitation
    ] = Field(
        default_factory=list,
    )

    validated_facts: list[
        WebPublicFinancialFact
    ] = Field(
        default_factory=list,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )