from __future__ import annotations

import re
from typing import Any

from app.agents.contracts import (
    AgentName,
    AgentRequest,
    AgentResult,
    AgentTask,
    ExecutionContext,
)
from app.agents.specialist_inputs import (
    CalculationAgentInput,
    ChartAgentInput,
    DataAnalysisAgentInput,
    DocumentAgentInput,
    FinancialFactAgentInput,
    SpecialistInput,
    WebResearchAgentInput,
)
from app.schemas.chart import ChartRequest
from app.schemas.tools import (
    FinancialCalculationType,
    FinancialCalculatorInput,
)


_NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")

class SpecialistInputResolutionError(ValueError):
    """Raised when a task cannot be converted into a safe typed specialist input."""


def _float_numbers(text: str) -> list[float]:
    return [float(value) for value in _NUMBER_PATTERN.findall(text)]


def _structured_calculation_from_metadata(
    request: AgentRequest,
) -> FinancialCalculatorInput | None:
    payload = request.metadata.get("calculation")
    if payload is None:
        return None
    try:
        return FinancialCalculatorInput.model_validate(payload)
    except Exception as exc:
        raise SpecialistInputResolutionError(
            "Request metadata contains an invalid structured calculation."
        ) from exc


def _direct_calculation_from_question(
    question: str,
) -> FinancialCalculatorInput:
    """Resolve only explicit numeric calculations.

    This intentionally does not guess numeric values from dependency evidence.
    Evidence-to-formula binding belongs to a later semantic binding layer.
    """
    lowered = question.lower()
    numbers = _float_numbers(question)

    if "cagr" in lowered:
        if len(numbers) < 3:
            raise SpecialistInputResolutionError(
                "CAGR requires explicit beginning, ending, and period values "
                "or request.metadata['calculation']."
            )
        return FinancialCalculatorInput(
            calculation_type=FinancialCalculationType.cagr,
            beginning_value=numbers[0],
            ending_value=numbers[1],
            periods=numbers[2],
        )

    if "margin" in lowered:
        if len(numbers) < 2:
            raise SpecialistInputResolutionError(
                "Margin requires explicit numerator and denominator values "
                "or request.metadata['calculation']."
            )
        return FinancialCalculatorInput(
            calculation_type=FinancialCalculationType.margin,
            numerator=numbers[0],
            denominator=numbers[1],
        )

    if "percentage of" in lowered or "percent of" in lowered:
        if len(numbers) < 2:
            raise SpecialistInputResolutionError(
                "Percentage-of requires two explicit numeric values."
            )
        return FinancialCalculatorInput(
            calculation_type=FinancialCalculationType.percentage_of,
            numerator=numbers[0],
            denominator=numbers[1],
        )

    if any(signal in lowered for signal in ("difference", "delta")):
        if len(numbers) < 2:
            raise SpecialistInputResolutionError(
                "Delta requires two explicit numeric values."
            )
        return FinancialCalculatorInput(
            calculation_type=FinancialCalculationType.delta,
            current_value=numbers[1],
            previous_value=numbers[0],
        )

    if any(
        signal in lowered
        for signal in ("growth", "increase", "decrease", "change", "percent", "percentage")
    ):
        if len(numbers) < 2:
            raise SpecialistInputResolutionError(
                "Growth calculation requires two explicit numeric values or "
                "request.metadata['calculation']."
            )
        return FinancialCalculatorInput(
            calculation_type=FinancialCalculationType.growth_rate,
            previous_value=numbers[0],
            current_value=numbers[1],
        )

    raise SpecialistInputResolutionError(
        "The calculation type could not be resolved safely."
    )


def _chart_request_from_metadata(
    request: AgentRequest,
    context: ExecutionContext,
) -> ChartRequest:
    payload = request.metadata.get("chart_request")
    if payload is None:
        raise SpecialistInputResolutionError(
            "Chart execution requires request.metadata['chart_request'] with "
            "validated chart_type/x/series fields."
        )
    if context.dataset_id is None:
        raise SpecialistInputResolutionError(
            "No dataset is available for chart execution."
        )

    candidate: dict[str, Any]
    if isinstance(payload, dict):
        candidate = dict(payload)
    else:
        raise SpecialistInputResolutionError(
            "request.metadata['chart_request'] must be an object."
        )
    candidate["dataset_id"] = context.dataset_id

    try:
        return ChartRequest.model_validate(candidate)
    except Exception as exc:
        raise SpecialistInputResolutionError(
            "The structured chart request is invalid."
        ) from exc


def resolve_specialist_input(
    *,
    task: AgentTask,
    request: AgentRequest,
    context: ExecutionContext,
    dependency_results: list[AgentResult],
) -> SpecialistInput:
    """Convert request/context into a strict 3I-B specialist input.

    Dependency results are supplied so later resolvers can bind reviewed
    evidence explicitly. 3I-D does not silently select numeric evidence.
    """
    if task.request_id != request.request_id or task.request_id != context.request_id:
        raise SpecialistInputResolutionError(
            "Task, request, and execution context identities do not match."
        )

    if task.agent_name == AgentName.document_agent:
        return DocumentAgentInput(
            query=request.question,
            document_ids=list(context.document_ids),
            top_k=context.top_k,
        )

    if task.agent_name == AgentName.web_research_agent:
        return WebResearchAgentInput(
            query=request.question,
            gap_reason=str(request.metadata.get("web_gap_reason") or "") or None,
            trusted_domains=list(context.trusted_web_domains),
            max_results=max(1, min(8, context.limits.max_web_fetches)),
            extract_structured_facts=bool(
                request.metadata.get("extract_web_structured_facts", False)
            ),
        )

    if task.agent_name == AgentName.financial_fact_agent:
        if not context.document_ids:
            raise SpecialistInputResolutionError(
                "Financial fact extraction requires request-scoped documents."
            )
        return FinancialFactAgentInput(
            document_ids=list(context.document_ids[:3]),
            query=request.question[:2000],
            requested_metrics=list(
                request.metadata.get("requested_metrics", [])
            )[:20],
        )

    if task.agent_name == AgentName.data_analysis_agent:
        if context.dataset_id is None:
            raise SpecialistInputResolutionError(
                "Data analysis requires a request-scoped dataset."
            )
        return DataAnalysisAgentInput(dataset_id=context.dataset_id)

    if task.agent_name == AgentName.calculation_agent:
        calculation = _structured_calculation_from_metadata(request)
        if calculation is None:
            calculation = _direct_calculation_from_question(request.question)
        return CalculationAgentInput(calculation=calculation)

    if task.agent_name == AgentName.chart_agent:
        return ChartAgentInput(
            request=_chart_request_from_metadata(request, context)
        )

    raise SpecialistInputResolutionError(
        f"No 3I-D input resolver exists for {task.agent_name.value}."
    )
