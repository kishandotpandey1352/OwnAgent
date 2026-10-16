from __future__ import annotations

from typing import Annotated

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Query,
)

from app.schemas.fact_api import (
    DocumentFinancialFactsResponse,
)

from app.services.fact_query_service import (
    FactQueryError,
    list_document_facts,
)

from typing import Literal

from app.schemas.fact_charts import (
    FinancialFactChartResponse,
)

from app.services.fact_chart_service import (
    FactChartError,
    build_document_fact_chart,
)


router = APIRouter(
    prefix="/facts",
    tags=["financial-facts"],
)


def _resolve_user_id(
    x_user_id: Annotated[
        str | None,
        Header(alias="X-User-Id"),
    ] = None,
) -> str:
    # Local development fallback.
    #
    # When real authentication is added,
    # replace this with the authenticated
    # user ID from your auth dependency.
    return (
        x_user_id
        or "local-demo-user"
    )


@router.get(
    "/documents/{document_id}",
    response_model=(
        DocumentFinancialFactsResponse
    ),
)
def get_document_facts(
    document_id: str,
    status: str = Query(
        default="validated",
        pattern=(
            "^(all|pending|validated|"
            "rejected|conflict)$"
        ),
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    x_user_id: Annotated[
        str | None,
        Header(alias="X-User-Id"),
    ] = None,
) -> DocumentFinancialFactsResponse:
    resolved_user_id = (
        x_user_id
        or "local-demo-user"
    )

    try:
        return list_document_facts(
            user_id=resolved_user_id,
            document_id=document_id,
            status=status,
            offset=offset,
            limit=limit,
        )

    except FactQueryError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to load financial "
                f"facts: {type(error).__name__}: "
                f"{error}"
            ),
        ) from error
@router.get(
    "/documents/{document_id}/chart",
    response_model=(
        FinancialFactChartResponse
    ),
)
def get_document_fact_chart(
    document_id: str,
    metric_key: str = Query(
        min_length=1,
        max_length=300,
    ),
    chart_type: Literal[
        "auto",
        "line",
        "bar",
    ] = Query(
        default="auto",
    ),
    company: str | None = Query(
        default=None,
    ),
    category: str | None = Query(
        default=None,
    ),
    statement_type: str | None = Query(
        default=None,
    ),
    x_user_id: Annotated[
        str | None,
        Header(
            alias="X-User-Id"
        ),
    ] = None,
) -> FinancialFactChartResponse:
    user_id = (
        x_user_id
        or "local-demo-user"
    )

    try:
        return (
            build_document_fact_chart(
                user_id=user_id,
                document_id=(
                    document_id
                ),
                metric_key=(
                    metric_key
                ),
                chart_type=(
                    chart_type
                ),
                company=company,
                category=category,
                statement_type=(
                    statement_type
                ),
            )
        )

    except FactChartError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to build "
                "financial fact chart: "
                f"{type(error).__name__}: "
                f"{error}"
            ),
        ) from error