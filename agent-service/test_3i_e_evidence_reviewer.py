from decimal import Decimal

from app.agents.contracts import (
    AgentEvidence,
    AgentName,
    AgentResult,
    AgentStatus,
    EvidenceSource,
    EvidenceSourceType,
)
from app.agents.review import EvidenceReviewStatus, EvidenceReviewer


REQ = "req-3ie"


def result(evidence):
    return AgentResult(
        task_id="task-1",
        request_id=REQ,
        agent_name=AgentName.document_agent,
        status=AgentStatus.completed,
        evidence=evidence,
    )


def source(kind: EvidenceSourceType, source_id: str, **kwargs):
    return EvidenceSource(source_type=kind, source_id=source_id, **kwargs)


def test_validated_document_evidence():
    e = AgentEvidence(
        evidence_id="ev-1",
        source_agent=AgentName.financial_fact_agent,
        source=source(EvidenceSourceType.document, "chunk-1", document_id="doc-1", page_number=1),
        metric="revenue",
        raw_value="Revenue was 100",
        normalized_numeric_value=Decimal("100"),
        period_label="FY2024",
        snippet="Revenue was 100",
        confidence=0.95,
    )
    summary = EvidenceReviewer().review(request_id=REQ, agent_results=[result([e])])
    assert summary.overall_status == EvidenceReviewStatus.validated
    assert summary.validated_evidence_ids == ["ev-1"]


def test_missing_period_is_partial():
    e = AgentEvidence(
        evidence_id="ev-2",
        source_agent=AgentName.financial_fact_agent,
        source=source(EvidenceSourceType.document, "chunk-2", document_id="doc-1", page_number=2),
        metric="revenue",
        raw_value="Revenue was 100",
        normalized_numeric_value=Decimal("100"),
        snippet="Revenue was 100",
    )
    summary = EvidenceReviewer().review(request_id=REQ, agent_results=[result([e])])
    assert summary.overall_status == EvidenceReviewStatus.partial
    assert summary.partial_evidence_ids == ["ev-2"]


def test_missing_web_url_is_unsupported():
    e = AgentEvidence(
        evidence_id="ev-3",
        source_agent=AgentName.web_research_agent,
        source=source(EvidenceSourceType.web, "web-3"),
        metric="revenue",
        raw_value="100",
        normalized_numeric_value=Decimal("100"),
        period_label="FY2024",
    )
    summary = EvidenceReviewer().review(request_id=REQ, agent_results=[result([e])])
    assert summary.overall_status == EvidenceReviewStatus.unsupported
    assert summary.unsupported_evidence_ids == ["ev-3"]


def test_conflicting_numeric_evidence():
    a = AgentEvidence(
        evidence_id="ev-a",
        source_agent=AgentName.financial_fact_agent,
        source=source(EvidenceSourceType.document, "chunk-a", document_id="doc-1", page_number=1),
        entity="Ambac",
        metric="commission income",
        raw_value="100",
        normalized_numeric_value=Decimal("100"),
        currency="USD",
        period_label="FY2024",
        snippet="100",
    )
    b = AgentEvidence(
        evidence_id="ev-b",
        source_agent=AgentName.web_research_agent,
        source=source(EvidenceSourceType.web, "web-1", url="https://example.com"),
        entity="Ambac",
        metric="commission income",
        raw_value="120",
        normalized_numeric_value=Decimal("120"),
        currency="USD",
        period_label="FY2024",
        snippet="120",
    )
    summary = EvidenceReviewer().review(request_id=REQ, agent_results=[result([a, b])])
    assert summary.overall_status == EvidenceReviewStatus.conflict
    assert set(summary.conflict_evidence_ids) == {"ev-a", "ev-b"}



def test_conflicting_financial_dimensions():
    a = AgentEvidence(
        evidence_id="ev-dim-a",
        source_agent=AgentName.financial_fact_agent,
        source=source(EvidenceSourceType.document, "chunk-dim-a", document_id="doc-1", page_number=1),
        entity="Ambac",
        metric="revenue",
        raw_value="100",
        normalized_numeric_value=Decimal("100"),
        currency="USD",
        scale="million",
        period_label="FY2024",
        snippet="Revenue was USD 100 million",
    )
    b = AgentEvidence(
        evidence_id="ev-dim-b",
        source_agent=AgentName.web_research_agent,
        source=source(EvidenceSourceType.web, "web-dim-b", url="https://example.com"),
        entity="Ambac",
        metric="revenue",
        raw_value="100",
        normalized_numeric_value=Decimal("100"),
        currency="GBP",
        scale="million",
        period_label="FY2024",
        snippet="Revenue was GBP 100 million",
    )
    summary = EvidenceReviewer().review(request_id=REQ, agent_results=[result([a, b])])
    assert summary.overall_status == EvidenceReviewStatus.conflict
    assert set(summary.conflict_evidence_ids) == {"ev-dim-a", "ev-dim-b"}

def test_empty_evidence_is_insufficient():
    summary = EvidenceReviewer().review(request_id=REQ, agent_results=[result([])])
    assert summary.overall_status == EvidenceReviewStatus.insufficient


def main():
    test_validated_document_evidence()
    test_missing_period_is_partial()
    test_missing_web_url_is_unsupported()
    test_conflicting_numeric_evidence()
    test_conflicting_financial_dimensions()
    test_empty_evidence_is_insufficient()
    print("PASS: 3I-E evidence reviewer validates, flags partial/unsupported evidence, and detects conflicts.")


if __name__ == "__main__":
    main()
