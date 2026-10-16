from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.agents.contracts import AgentEvidence, EvidenceReviewStatus


class ReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceReview(ReviewModel):
    schema_version: str = "EvidenceReview.v2"
    evidence_id: str = Field(min_length=1, max_length=200)
    status: EvidenceReviewStatus
    reasons: list[str] = Field(default_factory=list, max_length=20)
    reviewed_evidence: AgentEvidence


class EvidenceReviewSummary(ReviewModel):
    schema_version: str = "EvidenceReviewSummary.v2"
    request_id: str = Field(min_length=1, max_length=200)
    overall_status: EvidenceReviewStatus
    reviews: list[EvidenceReview] = Field(default_factory=list, max_length=256)
    validated_evidence_ids: list[str] = Field(default_factory=list, max_length=256)
    partial_evidence_ids: list[str] = Field(default_factory=list, max_length=256)
    conflict_evidence_ids: list[str] = Field(default_factory=list, max_length=256)
    unsupported_evidence_ids: list[str] = Field(default_factory=list, max_length=256)
    insufficient_evidence_ids: list[str] = Field(default_factory=list, max_length=256)
    warnings: list[str] = Field(default_factory=list, max_length=100)

    def usable_evidence(self) -> list[AgentEvidence]:
        allowed = {
            EvidenceReviewStatus.validated,
            EvidenceReviewStatus.partial,
        }
        return [
            item.reviewed_evidence
            for item in self.reviews
            if item.status in allowed
        ]
