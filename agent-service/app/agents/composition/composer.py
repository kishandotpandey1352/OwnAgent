from __future__ import annotations

import json
from decimal import Decimal
from typing import Callable

from app.agents.contracts import AgentEvidence, AgentRequest, EvidenceReviewStatus
from app.agents.composition.models import AnswerCitation, AnswerClaim, ComposedAnswer
from app.agents.review.models import EvidenceReviewSummary

AnswerRenderer = Callable[[dict], str]
AnswerValidator = Callable[[str, list[AnswerClaim]], bool]


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    return format(normalized, "f")


def _claim_text(item: AgentEvidence) -> str:
    if item.metric and item.normalized_numeric_value is not None:
        value = _format_decimal(Decimal(item.normalized_numeric_value))
        parts = [item.metric, value]
        if item.currency:
            parts.append(item.currency)
        if item.scale:
            parts.append(f"scale={item.scale}")
        if item.period_label:
            parts.append(item.period_label)
        return ": ".join([parts[0], " ".join(parts[1:])])
    if item.raw_value:
        return item.raw_value.strip()
    if item.snippet:
        return item.snippet.strip()
    return f"Evidence {item.evidence_id} was validated."


def _citation(item: AgentEvidence) -> AnswerCitation:
    source = item.source
    return AnswerCitation(
        evidence_id=item.evidence_id,
        source_type=source.source_type.value,
        source_id=source.source_id,
        title=source.title,
        url=source.url,
        document_id=source.document_id,
        page_number=source.page_number,
    )


class AnswerComposer:
    """Grounded presentation layer over reviewed evidence.

    An optional LLM renderer may improve phrasing, but it is never trusted as a
    grounding authority. LLM-rendered prose is accepted only when a grounding
    validator is also injected and explicitly passes the rendered text. The
    deterministic evidence-backed presentation is the safe fallback.
    """

    version = "3I-F.1.1.0"

    def __init__(
        self,
        renderer: AnswerRenderer | None = None,
        validator: AnswerValidator | None = None,
    ) -> None:
        self._renderer = renderer
        self._validator = validator

    def compose(
        self,
        *,
        request: AgentRequest,
        review: EvidenceReviewSummary,
    ) -> ComposedAnswer:
        if request.request_id != review.request_id:
            raise ValueError("Review request_id does not match AgentRequest.")

        usable_reviews = [
            item
            for item in review.reviews
            if item.status in {
                EvidenceReviewStatus.validated,
                EvidenceReviewStatus.partial,
            }
        ]

        warnings = list(review.warnings)
        if review.conflict_evidence_ids:
            warnings.append("Conflicting evidence was excluded from composition.")
        if review.unsupported_evidence_ids:
            warnings.append("Unsupported evidence was excluded from composition.")

        claims = [
            AnswerClaim(
                text=_claim_text(item.reviewed_evidence),
                evidence_ids=[item.evidence_id],
                numeric_claim=item.reviewed_evidence.normalized_numeric_value is not None,
            )
            for item in usable_reviews
        ]
        citations = [_citation(item.reviewed_evidence) for item in usable_reviews]

        if not claims:
            if review.overall_status == EvidenceReviewStatus.conflict:
                answer = (
                    "I found conflicting evidence and cannot provide a single "
                    "grounded answer without resolving that conflict."
                )
            else:
                answer = (
                    "I do not have enough validated evidence to provide a "
                    "grounded answer."
                )
            return ComposedAnswer(
                request_id=request.request_id,
                answer=answer,
                claims=[],
                citations=[],
                grounded=False,
                warnings=warnings,
            )

        deterministic_answer = "\n".join(f"- {claim.text}" for claim in claims)
        renderer_name = "deterministic"
        answer = deterministic_answer

        if self._renderer is not None:
            if self._validator is None:
                warnings.append(
                    "LLM renderer was not used because no grounding validator was configured."
                )
            else:
                payload = {
                    "question": request.question,
                    "claims": [claim.model_dump(mode="json") for claim in claims],
                    "citations": [citation.model_dump(mode="json") for citation in citations],
                    "rules": [
                        "Use only supplied claims.",
                        "Do not calculate new values.",
                        "Do not invent sources or facts.",
                        "Do not silently resolve conflicts.",
                    ],
                }
                try:
                    rendered = self._renderer(payload)
                    if not isinstance(rendered, str) or not rendered.strip():
                        raise ValueError("Renderer returned an empty answer.")
                    rendered = rendered.strip()
                    if not self._validator(rendered, claims):
                        raise ValueError("Rendered answer failed grounding validation.")
                    answer = rendered
                    renderer_name = getattr(self._renderer, "__name__", "llm_renderer")
                except Exception:
                    warnings.append(
                        "Answer renderer failed grounding/validation; deterministic grounded presentation was used."
                    )

        return ComposedAnswer(
            request_id=request.request_id,
            answer=answer,
            claims=claims,
            citations=citations,
            grounded=True,
            renderer=renderer_name,
            warnings=warnings,
        )

    @staticmethod
    def renderer_payload_json(payload: dict) -> str:
        return json.dumps(payload, sort_keys=True, ensure_ascii=True)
