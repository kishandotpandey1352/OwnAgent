from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.chart import ChartRequest
from app.schemas.tools import FinancialCalculatorInput


class SpecialistInput(BaseModel):
    """Strict typed input boundary for a specialist-agent wrapper."""

    model_config = ConfigDict(extra="forbid")


class DocumentAgentInput(SpecialistInput):
    query: str = Field(min_length=1, max_length=4000)
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    top_k: int = Field(default=6, ge=1, le=20)


class WebResearchAgentInput(SpecialistInput):
    query: str = Field(min_length=1, max_length=4000)
    gap_reason: str | None = Field(default=None, max_length=2000)
    trusted_domains: list[str] = Field(default_factory=list, max_length=25)
    max_results: int = Field(default=8, ge=1, le=20)
    extract_structured_facts: bool = False


class FinancialFactAgentInput(SpecialistInput):
    document_ids: list[str] = Field(min_length=1, max_length=3)
    query: str = Field(min_length=1, max_length=2000)
    requested_metrics: list[str] = Field(default_factory=list, max_length=20)
    max_facts_per_document: int = Field(default=60, ge=1, le=100)
    max_returned_facts: int = Field(default=40, ge=1, le=100)


class DataAnalysisAgentInput(SpecialistInput):
    dataset_id: str = Field(min_length=1, max_length=200)


class CalculationAgentInput(SpecialistInput):
    calculation: FinancialCalculatorInput


class ChartAgentInput(SpecialistInput):
    request: ChartRequest
