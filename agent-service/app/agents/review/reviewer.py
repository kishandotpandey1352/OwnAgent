from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from math import isclose
from typing import Iterable

from app.agents.contracts import (
    AgentEvidence,
    AgentResult,
    AgentStatus,
    EvidenceReviewStatus,
    EvidenceSourceType,
)
from app.agents.review.models import EvidenceReview, EvidenceReviewSummary


def _norm(value: str | None) -> str:
    return " ".join((value or "").strip().casefold().split())


def _period_key(item: AgentEvidence) -> tuple[str, str, str]:
    return (
        _norm(item.period_label),
        item.period_start.isoformat() if item.period_start else "",
        item.period_end.isoformat() if item.period_end else "",
    )


def _source_reasons(item: AgentEvidence) -> list[str]:
    reasons: list[str] = []
    source = item.source

    if not source.source_id.strip():
        reasons.append("Evidence source_id is missing.")

    if source.source_type == EvidenceSourceType.document:
        if not source.document_id:
            reasons.append("Document evidence is missing document_id.")
        if not source.chunk_id and not source.page_number:
            reasons.append("Document evidence has no chunk/page locator.")
        if not item.snippet and not item.raw_value:
            reasons.append("Document evidence has no supporting text/value.")

    elif source.source_type == EvidenceSourceType.web:
        if not source.url:
            reasons.append("Web evidence is missing source URL.")
        if not item.snippet and not item.raw_value:
            reasons.append("Web evidence has no supporting text/value.")

    elif source.source_type == EvidenceSourceType.dataset:
        if not item.snippet and not item.raw_value and item.normalized_numeric_value is None:
            reasons.append("Dataset evidence contains no usable value or summary.")

    elif source.source_type == EvidenceSourceType.calculation:
        lineage = item.calculation_lineage
        if lineage is None:
            reasons.append("Calculation evidence is missing calculation lineage.")
        elif not lineage.input_evidence_ids:
            reasons.append("Calculation evidence has no input evidence IDs.")

    return reasons


def _completeness_reasons(item: AgentEvidence) -> list[str]:
    reasons: list[str] = []
    if item.metric and item.normalized_numeric_value is not None:
        if not any(_period_key(item)):
            reasons.append("Numeric financial evidence is missing a period.")
    if item.currency and len(item.currency.strip()) < 3:
        reasons.append("Currency code is malformed.")
    if item.confidence is not None and item.confidence < 0.35:
        reasons.append("Evidence confidence is below the review threshold.")
    return reasons


def _conflicts(items: list[AgentEvidence]) -> dict[str, set[str]]:
    """Return conservative conflicts for comparable financial evidence.

    We first group by the semantic identity of the fact (entity, metric and
    period). Currency/scale/unit are *dimensions of that fact*, not part of the
    identity key. If two sources disagree on those dimensions we surface the
    ambiguity rather than silently treating the facts as unrelated. If the
    dimensions match, differing normalized numeric values are also conflicts.
    """

    grouped: dict[tuple, list[AgentEvidence]] = defaultdict(list)
    for item in items:
        if item.metric is None or item.normalized_numeric_value is None:
            continue
        key = (
            _norm(item.entity),
            _norm(item.metric),
            _period_key(item),
        )
        grouped[key].append(item)

    output: dict[str, set[str]] = defaultdict(set)
    for group in grouped.values():
        if len(group) < 2:
            continue
        for index, left in enumerate(group):
            for right in group[index + 1 :]:
                left_dimensions = (
                    _norm(left.currency),
                    _norm(left.scale),
                    _norm(left.unit),
                )
                right_dimensions = (
                    _norm(right.currency),
                    _norm(right.scale),
                    _norm(right.unit),
                )
                dimension_mismatch = left_dimensions != right_dimensions

                left_value = Decimal(left.normalized_numeric_value)
                right_value = Decimal(right.normalized_numeric_value)
                value_mismatch = not isclose(
                    float(left_value),
                    float(right_value),
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )

                if dimension_mismatch or value_mismatch:
                    output[left.evidence_id].add(right.evidence_id)
                    output[right.evidence_id].add(left.evidence_id)
    return output


class EvidenceReviewer:
    """Deterministic evidence reviewer.

    The reviewer never retrieves new data and never calculates new facts. It
    validates provenance, completeness, conservative numeric consistency and
    calculation lineage for evidence already produced by specialists.
    """

    version = "3I-E.2.0.0"

    def review(
        self,
        *,
        request_id: str,
        agent_results: Iterable[AgentResult],
    ) -> EvidenceReviewSummary:
        warnings: list[str] = []
        evidence: list[AgentEvidence] = []

        for result in agent_results:
            if result.request_id != request_id:
                warnings.append(
                    f"Ignored task {result.task_id}: request_id mismatch."
                )
                continue
            if result.status in {AgentStatus.completed, AgentStatus.partial}:
                evidence.extend(result.evidence)
            elif result.status in {AgentStatus.failed, AgentStatus.timed_out}:
                warnings.append(
                    f"Task {result.task_id} did not complete successfully."
                )

        if not evidence:
            return EvidenceReviewSummary(
                request_id=request_id,
                overall_status=EvidenceReviewStatus.insufficient,
                warnings=warnings + ["No specialist evidence was available."],
            )

        ids = [item.evidence_id for item in evidence]
        duplicate_ids = {item for item in ids if ids.count(item) > 1}
        evidence_id_set = set(ids)
        conflicts = _conflicts(evidence)
        reviews: list[EvidenceReview] = []

        for item in evidence:
            reasons: list[str] = []
            status = EvidenceReviewStatus.validated

            if item.evidence_id in duplicate_ids:
                reasons.append("Duplicate evidence_id detected.")
                status = EvidenceReviewStatus.unsupported

            if item.evidence_id in conflicts:
                reasons.append(
                    "Conflicts with evidence: "
                    + ", ".join(sorted(conflicts[item.evidence_id]))
                )
                status = EvidenceReviewStatus.conflict

            source_reasons = _source_reasons(item)
            if source_reasons and status != EvidenceReviewStatus.conflict:
                reasons.extend(source_reasons)
                status = EvidenceReviewStatus.unsupported

            lineage = item.calculation_lineage
            if lineage is not None:
                missing_lineage = set(lineage.input_evidence_ids) - evidence_id_set
                if missing_lineage:
                    reasons.append(
                        "Calculation lineage references unknown evidence: "
                        + ", ".join(sorted(missing_lineage))
                    )
                    status = EvidenceReviewStatus.unsupported

            completeness = _completeness_reasons(item)
            if completeness and status == EvidenceReviewStatus.validated:
                reasons.extend(completeness)
                status = EvidenceReviewStatus.partial

            reviewed = item.model_copy(update={"review_status": status})
            reviews.append(
                EvidenceReview(
                    evidence_id=item.evidence_id,
                    status=status,
                    reasons=reasons,
                    reviewed_evidence=reviewed,
                )
            )

        by_status = {
            state: [r.evidence_id for r in reviews if r.status == state]
            for state in EvidenceReviewStatus
        }

        if by_status[EvidenceReviewStatus.conflict]:
            overall = EvidenceReviewStatus.conflict
        elif by_status[EvidenceReviewStatus.unsupported]:
            overall = EvidenceReviewStatus.unsupported
        elif by_status[EvidenceReviewStatus.validated] and by_status[EvidenceReviewStatus.partial]:
            overall = EvidenceReviewStatus.partial
        elif by_status[EvidenceReviewStatus.validated]:
            overall = EvidenceReviewStatus.validated
        elif by_status[EvidenceReviewStatus.partial]:
            overall = EvidenceReviewStatus.partial
        else:
            overall = EvidenceReviewStatus.insufficient

        return EvidenceReviewSummary(
            request_id=request_id,
            overall_status=overall,
            reviews=reviews,
            validated_evidence_ids=by_status[EvidenceReviewStatus.validated],
            partial_evidence_ids=by_status[EvidenceReviewStatus.partial],
            conflict_evidence_ids=by_status[EvidenceReviewStatus.conflict],
            unsupported_evidence_ids=by_status[EvidenceReviewStatus.unsupported],
            insufficient_evidence_ids=by_status[EvidenceReviewStatus.insufficient],
            warnings=warnings,
        )


def review_agent_results(
    *,
    request_id: str,
    agent_results: Iterable[AgentResult],
) -> EvidenceReviewSummary:
    return EvidenceReviewer().review(
        request_id=request_id,
        agent_results=agent_results,
    )
