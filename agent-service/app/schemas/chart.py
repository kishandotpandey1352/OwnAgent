from typing import Any, Literal

from pydantic import BaseModel, Field


ChartType = Literal[
    "line",
    "bar",
    "scatter",
    "area",
    "table",
]


class ChartRequest(BaseModel):
    dataset_id: str = Field(
        min_length=1,
    )

    chart_type: ChartType

    x: str | None = None

    series: list[str] = Field(
        default_factory=list,
    )

    title: str | None = None

    max_rows: int = Field(
        default=500,
        ge=10,
        le=2000,
    )


class ChartSpecResponse(BaseModel):
    ok: bool = True

    dataset_id: str
    file_name: str

    chart_type: ChartType

    title: str

    x: str | None = None

    series: list[str] = Field(
        default_factory=list,
    )

    data: list[
        dict[str, Any]
    ] = Field(
        default_factory=list,
    )

    source_row_count: int
    chart_row_count: int

    sampled: bool = False

    explanation: str

    source_coverage: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
    )

    warnings: list[str] = Field(
        default_factory=list,
    )