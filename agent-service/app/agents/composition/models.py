from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CompositionModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AnswerCitation(CompositionModel):
    schema_version: str = "AnswerCitation.v1"
    evidence_id: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=50)
    source_id: str = Field(min_length=1, max_length=500)
    title: str | None = Field(default=None, max_length=500)
    url: str | None = Field(default=None, max_length=2000)
    document_id: str | None = Field(default=None, max_length=200)
    page_number: int | None = Field(default=None, ge=1)


class AnswerClaim(CompositionModel):
    schema_version: str = "AnswerClaim.v1"
    text: str = Field(min_length=1, max_length=4000)
    evidence_ids: list[str] = Field(min_length=1, max_length=25)
    numeric_claim: bool = False


class ComposedAnswer(CompositionModel):
    schema_version: str = "ComposedAnswer.v1"
    request_id: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=20000)
    claims: list[AnswerClaim] = Field(default_factory=list, max_length=100)
    citations: list[AnswerCitation] = Field(default_factory=list, max_length=250)
    grounded: bool
    renderer: str = Field(default="deterministic", max_length=100)
    warnings: list[str] = Field(default_factory=list, max_length=100)
