from __future__ import annotations

from uuid import uuid4

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
)

from app.graphs.finance_memory_graph import (
    build_finance_memory_graph,
)

from app.schemas.agent import (
    AgentAnalyzeRequest,
    AgentAnalyzeResponse,
)

from app.services.web_citation_guard import (
    enforce_web_citation_integrity,
)
from app.services.web_product_response import (
    build_web_product_summary,
    sanitize_tool_results_for_public,
)


router = APIRouter(
    prefix="/agents",
    tags=[
        "agents",
    ],
)


# =========================================================
# User identity
# =========================================================


def get_user_id(
    request_user_id: str | None,
    header_user_id: str | None,
) -> str:
    return (
        request_user_id
        or header_user_id
        or "local-demo-user"
    )


# =========================================================
# Agent analysis
# =========================================================


@router.post(
    "/analyze",
    response_model=(
        AgentAnalyzeResponse
    ),
)
def analyze(
    request: AgentAnalyzeRequest,
    x_user_id: str | None = Header(
        default=None
    ),
):
    request_id = str(
        uuid4()
    )

    effective_dataset_id = (
        request.dataset_id
    )

    # -----------------------------------------------------
    # Phase 3F
    # Keep dataset_id and chart_request.dataset_id aligned.
    # -----------------------------------------------------

    if request.chart_request:
        chart_dataset_id = (
            request
            .chart_request
            .dataset_id
        )

        if (
            effective_dataset_id
            and effective_dataset_id
            != chart_dataset_id
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "dataset_id and "
                    "chart_request.dataset_id "
                    "must refer to the same "
                    "dataset."
                ),
            )

        effective_dataset_id = (
            chart_dataset_id
        )

    try:
        user_id = (
            get_user_id(
                request.user_id,
                x_user_id,
            )
        )

        graph = (
            build_finance_memory_graph()
        )

        # =================================================
        # LangGraph request state
        # =================================================

        result = graph.invoke(
            {
                "request_id":
                    request_id,

                "user_id":
                    user_id,

                "question":
                    request
                    .question
                    .strip(),

                "provider_id":
                    request
                    .provider_id,

                # -----------------------------------------
                # Phase 3D
                # Uploaded-document RAG
                # -----------------------------------------

                "use_documents":
                    request
                    .use_documents,

                "document_ids":
                    request
                    .document_ids,

                "top_k":
                    request
                    .top_k,

                # -----------------------------------------
                # Phase 3E / 3F
                # Structured data and charting
                # -----------------------------------------

                "dataset_id":
                    effective_dataset_id,

                "chart_request":
                    request
                    .chart_request,

                # -----------------------------------------
                # Phase 3H-A+
                # Explicit web fallback controls
                # -----------------------------------------

                "allow_web_fallback":
                    request
                    .allow_web_fallback,

                "trusted_web_domains":
                    request
                    .trusted_web_domains,

                # -----------------------------------------
                # General request metadata
                # -----------------------------------------

                "metadata":
                    request
                    .metadata,
            }
        )

        tool_plan = (
            result.get(
                "tool_plan"
            )
        )

        tool_results = (
            result.get(
                "tool_results",
                [],
            )
            or []
        )

        # =================================================
        # Phase 3H-F-A
        # Public product response
        # =================================================

        web_fallback_used = bool(
            result.get(
                "web_fallback_used",
                False,
            )
        )

        web_fallback_available = bool(
            result.get(
                "web_fallback_available",
                False,
            )
        )

        web_fallback_reason = (
            result.get(
                "web_fallback_reason"
            )
        )

        web_research = (
            build_web_product_summary(
                tool_results=(
                    tool_results
                ),

                web_fallback_used=(
                    web_fallback_used
                ),

                web_fallback_available=(
                    web_fallback_available
                ),

                web_fallback_reason=(
                    web_fallback_reason
                ),
            )
        )

        # =================================================
        # Phase 3H-F-F
        # Deterministic Web Source citation integrity
        # =================================================

        citation_guard = (
            enforce_web_citation_integrity(
                answer=str(
                    result.get(
                        "answer",
                        "",
                    )
                    or ""
                ),
                web_research=(
                    web_research
                ),
            )
        )

        if (
            citation_guard
            .invalid_citations
        ):
            warnings = list(
                web_research.warnings
                or []
            )

            warning = (
                "One or more invalid web citation "
                "references were removed from the "
                "generated answer."
            )

            if warning not in warnings:
                warnings.append(
                    warning
                )

            web_research = (
                web_research.model_copy(
                    update={
                        "warnings":
                            warnings,
                    }
                )
            )

        # IMPORTANT:
        #
        # Raw web_research tool output must never be sent
        # directly to the browser.
        public_tool_results = (
            sanitize_tool_results_for_public(
                tool_results
            )
        )

        # =================================================
        # Response
        # =================================================

        return (
            AgentAnalyzeResponse(
                ok=True,

                request_id=(
                    request_id
                ),

                answer=(
                    citation_guard.answer
                ),

                memory_context=(
                    result.get(
                        "memory_context",
                        "",
                    )
                ),

                memory_used_count=(
                    result.get(
                        "memory_used_count",
                        0,
                    )
                ),

                model=(
                    result.get(
                        "model",
                        "",
                    )
                ),

                tool_plan=(
                    tool_plan
                    .model_dump(
                        mode="json"
                    )
                    if tool_plan
                    else None
                ),

                # 3H-F-A:
                # browser-safe version only.
                tool_results=(
                    public_tool_results
                ),

                grounding=(
                    result.get(
                        "grounding"
                    )
                ),

                # -----------------------------------------
                # Phase 3H-A control state
                # -----------------------------------------

                web_fallback_used=(
                    web_fallback_used
                ),

                web_fallback_available=(
                    web_fallback_available
                ),

                web_fallback_reason=(
                    web_fallback_reason
                ),

                # -----------------------------------------
                # Phase 3H-F-A public web evidence
                # -----------------------------------------

                web_research=(
                    web_research
                ),
            )
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(
                error
            ),
        ) from error