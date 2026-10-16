from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ColumnType = Literal[
    "date",
    "numeric",
    "boolean",
    "string",
]

NumericFormat = Literal[
    "number",
    "currency",
    "percentage",
]

ChartType = Literal[
    "line",
    "bar",
    "scatter",
    "table",
]


class NumericSummary(BaseModel):
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    median: float | None = None
    std: float | None = None
    q1: float | None = None
    q3: float | None = None
    sum: float | None = None


class ColumnProfile(BaseModel):
    name: str
    inferred_type: ColumnType

    non_null_count: int
    missing_count: int
    missing_percent: float

    unique_count: int

    numeric_format: NumericFormat | None = None
    numeric_summary: NumericSummary | None = None

    example_values: list[Any] = Field(default_factory=list)


class ChartSuggestion(BaseModel):
    chart_type: ChartType
    x: str | None = None
    series: list[str] = Field(default_factory=list)
    reason: str


class DatasetMetadata(BaseModel):
    dataset_id: str
    user_id: str

    file_name: str

    row_count: int
    column_count: int
    size_bytes: int

    created_at: datetime


class DatasetUploadResponse(BaseModel):
    ok: bool = True

    dataset_id: str
    file_name: str

    row_count: int
    column_count: int
    size_bytes: int

    created_at: datetime


class DatasetProfileResponse(BaseModel):
    ok: bool = True

    dataset_id: str
    file_name: str

    row_count: int
    column_count: int

    columns: list[ColumnProfile] = Field(default_factory=list)

    sample_rows: list[dict[str, Any]] = Field(default_factory=list)

    chart_suggestions: list[ChartSuggestion] = Field(
        default_factory=list
    )


class DatasetDeleteResponse(BaseModel):
    ok: bool = True
    dataset_id: str
    deleted: bool