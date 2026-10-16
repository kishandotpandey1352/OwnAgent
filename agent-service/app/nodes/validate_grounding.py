import json

from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.graphs.state import FinanceAgentState
from app.schemas.grounding import GroundingValidation


def _document_sources(state: FinanceAgentState) -> list[dict]:
    for result in state.get("tool_results", []):
        if (
            result.tool_name.value == "document_search"
            and result.status.value == "completed"
        ):
            return result.output.get("sources", [])

    return []


def validate_grounding_node(
    state: FinanceAgentState,
) -> FinanceAgentState:
    if not state.get("use_documents", False):
        return state

    sources = _document_sources(state)

    if not sources:
        return {
            **state,
            "grounding": GroundingValidation(
                confidence="low",
                cited_source_numbers=[],
                unsupported_claims=["No retrieved sources were available."],
                should_refuse=True,
                reason="No evidence was retrieved.",
            ).model_dump(mode="json"),
        }

    model = ChatOpenAI(
        model=settings.agent_model,
        temperature=0,
        api_key=settings.openai_api_key,
    )

    validator = model.with_structured_output(GroundingValidation)

    prompt = f"""
You are a strict finance answer validator.

Check whether the answer is supported ONLY by the supplied document sources.

Question:
{state["question"]}

Answer:
{state.get("answer", "")}

Sources:
{json.dumps(sources, indent=2)}

Rules:
- High confidence only when important claims are clearly supported.
- Medium means mostly supported with minor gaps.
- Low means important claims are unsupported or evidence is insufficient.
- List unsupported claims.
- Set should_refuse=true when important factual claims rely on information
  outside the sources.
- Do not use outside knowledge.
""".strip()

    validation = validator.invoke(prompt)

    new_state = {
        **state,
        "grounding": validation.model_dump(mode="json"),
    }

    if validation.should_refuse or validation.confidence == "low":
        new_state["answer"] = (
            "I could not fully verify the answer from the retrieved "
            "document sources."
            + (
                f"\n\nReason: {validation.reason}"
                if validation.reason
                else ""
            )
            + "\n\nTry selecting a more relevant document or asking a "
            "narrower question."
        )

    return new_state