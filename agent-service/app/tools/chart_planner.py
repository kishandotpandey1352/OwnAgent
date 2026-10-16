import math
from typing import Any

import pandas as pd

from app.schemas.chart import (
    ChartRequest,
    ChartSpecResponse,
)
from app.services.csv_store import (
    load_csv_dataset,
)


class ChartBuildError(ValueError):
    pass


def _json_safe_value(
    value: Any,
) -> Any:
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if isinstance(
        value,
        (
            str,
            int,
            bool,
        ),
    ):
        return value

    if isinstance(
        value,
        float,
    ):
        if math.isfinite(value):
            return value

        return None

    if hasattr(
        value,
        "item",
    ):
        try:
            return _json_safe_value(
                value.item()
            )
        except Exception:
            pass

    return str(value)


def _safe_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        result = float(value)
    except (
        TypeError,
        ValueError,
    ):
        return None

    if not math.isfinite(result):
        return None

    return result


def _parse_numeric_series(
    series: pd.Series,
) -> pd.Series:
    """
    Convert common finance-style values to floats.

    Examples:
        "$12,500" -> 12500
        "£4,250"  -> 4250
        "15.7%"   -> 15.7
        "(3,500)" -> -3500
    """

    cleaned = (
        series
        .astype("string")
        .str.strip()
    )

    # Accounting negative notation:
    # (3500) -> -3500
    cleaned = cleaned.str.replace(
        r"^\((.*)\)$",
        r"-\1",
        regex=True,
    )

    # Remove common currency symbols,
    # grouping commas, and whitespace.
    cleaned = cleaned.str.replace(
        r"[$€£¥₹,\s]",
        "",
        regex=True,
    )

    cleaned = cleaned.str.replace(
        "%",
        "",
        regex=False,
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce",
    )


def _ensure_columns_exist(
    dataframe: pd.DataFrame,
    columns: list[str],
) -> None:
    missing_columns = [
        column
        for column in columns
        if column
        not in dataframe.columns
    ]

    if missing_columns:
        raise ChartBuildError(
            "Unknown dataset column(s): "
            + ", ".join(
                missing_columns
            )
        )


def _sample_dataframe(
    dataframe: pd.DataFrame,
    max_rows: int,
) -> tuple[
    pd.DataFrame,
    bool,
]:
    """
    Downsample across the full dataset instead of
    simply taking the first N rows.
    """

    row_count = len(
        dataframe
    )

    if row_count <= max_rows:
        return (
            dataframe.copy(),
            False,
        )

    step = (
        row_count
        / max_rows
    )

    indices = [
        min(
            int(index * step),
            row_count - 1,
        )
        for index
        in range(max_rows)
    ]

    return (
        dataframe
        .iloc[indices]
        .copy(),
        True,
    )


def _build_title(
    request: ChartRequest,
) -> str:
    if (
        request.title
        and request.title.strip()
    ):
        return request.title.strip()

    if (
        request.chart_type
        == "table"
    ):
        return "Dataset table"

    if request.series:
        series_label = ", ".join(
            request.series
        )

        if request.x:
            return (
                f"{series_label} by "
                f"{request.x}"
            )

        return series_label

    return "Data visualization"


def _build_explanation(
    request: ChartRequest,
) -> str:
    if request.chart_type == "line":
        return (
            "Line chart showing how the selected "
            "numeric series change across "
            f"{request.x}."
        )

    if request.chart_type == "area":
        return (
            "Area chart showing the magnitude and "
            "trend of the selected numeric series "
            f"across {request.x}."
        )

    if request.chart_type == "bar":
        return (
            "Bar chart comparing the selected "
            f"numeric series across {request.x}."
        )

    if request.chart_type == "scatter":
        return (
            "Scatter chart showing the relationship "
            f"between {request.x} and "
            f"{request.series[0]}."
        )

    return (
        "Table view of selected dataset values."
    )


def _build_table_spec(
    *,
    dataframe: pd.DataFrame,
    request: ChartRequest,
    file_name: str,
) -> ChartSpecResponse:
    selected_columns: list[str] = []

    if request.x:
        selected_columns.append(
            request.x
        )

    for column in request.series:
        if column not in selected_columns:
            selected_columns.append(
                column
            )

    # If the caller does not specify fields,
    # show the first 12 columns.
    if not selected_columns:
        selected_columns = [
            str(column)
            for column
            in dataframe.columns[:12]
        ]

    _ensure_columns_exist(
        dataframe,
        selected_columns,
    )

    source_row_count = len(
        dataframe
    )

    selected = dataframe[
        selected_columns
    ].copy()

    (
        selected,
        sampled,
    ) = _sample_dataframe(
        selected,
        request.max_rows,
    )

    rows: list[
        dict[str, Any]
    ] = []

    for _, row in selected.iterrows():
        rows.append(
            {
                column:
                    _json_safe_value(
                        row[column]
                    )
                for column
                in selected_columns
            }
        )

    warnings: list[str] = []

    if sampled:
        warnings.append(
            "The table was sampled because the "
            "dataset exceeded the configured "
            "chart row limit."
        )

    return ChartSpecResponse(
        dataset_id=request.dataset_id,
        file_name=file_name,
        chart_type="table",
        title=_build_title(
            request
        ),
        x=request.x,
        series=[
            column
            for column
            in selected_columns
            if column != request.x
        ],
        data=rows,
        source_row_count=source_row_count,
        chart_row_count=len(
            rows
        ),
        sampled=sampled,
        explanation=_build_explanation(
            request
        ),
        source_coverage=1.0,
        warnings=warnings,
    )


def build_chart_spec(
    *,
    user_id: str,
    request: ChartRequest,
) -> ChartSpecResponse:
    (
        metadata,
        dataframe,
    ) = load_csv_dataset(
        dataset_id=request.dataset_id,
        user_id=user_id,
    )

    if dataframe.empty:
        raise ChartBuildError(
            "The dataset does not contain any rows."
        )

    if request.chart_type == "table":
        return _build_table_spec(
            dataframe=dataframe,
            request=request,
            file_name=metadata.file_name,
        )

    if not request.x:
        raise ChartBuildError(
            "An x-axis column is required "
            "for this chart type."
        )

    if not request.series:
        raise ChartBuildError(
            "At least one series column "
            "is required."
        )

    if (
        request.chart_type
        == "scatter"
        and len(request.series) != 1
    ):
        raise ChartBuildError(
            "Scatter charts currently require "
            "exactly one y-axis series."
        )

    requested_columns = [
        request.x,
        *request.series,
    ]

    _ensure_columns_exist(
        dataframe,
        requested_columns,
    )

    working = dataframe[
        requested_columns
    ].copy()

    warnings: list[str] = []

    # ---------------------------------------------------------
    # Scatter charts require numeric X and Y values.
    # ---------------------------------------------------------

    if request.chart_type == "scatter":
        parsed_x = _parse_numeric_series(
            working[
                request.x
            ]
        )

        original_x_count = int(
            working[
                request.x
            ]
            .notna()
            .sum()
        )

        parsed_x_count = int(
            parsed_x
            .notna()
            .sum()
        )

        if parsed_x_count == 0:
            raise ChartBuildError(
                f"Scatter x-axis column "
                f"'{request.x}' does not contain "
                "numeric values."
            )

        invalid_x_count = (
            original_x_count
            - parsed_x_count
        )

        if invalid_x_count > 0:
            warnings.append(
                f"{invalid_x_count} value(s) in "
                f"'{request.x}' could not be parsed "
                "as numeric scatter coordinates."
            )

        working[
            request.x
        ] = parsed_x

    # ---------------------------------------------------------
    # Parse every series as numeric.
    # ---------------------------------------------------------

    total_source_values = 0
    total_valid_values = 0

    for column in request.series:
        original_series = working[
            column
        ]

        original_non_null = int(
            original_series
            .notna()
            .sum()
        )

        parsed = _parse_numeric_series(
            original_series
        )

        parsed_non_null = int(
            parsed
            .notna()
            .sum()
        )

        if parsed_non_null == 0:
            raise ChartBuildError(
                f"Column '{column}' does not "
                "contain numeric values that can "
                "be plotted."
            )

        invalid_count = (
            original_non_null
            - parsed_non_null
        )

        if invalid_count > 0:
            warnings.append(
                f"{invalid_count} value(s) in "
                f"'{column}' could not be parsed "
                "as numbers and will appear as gaps."
            )

        total_source_values += (
            original_non_null
        )

        total_valid_values += (
            parsed_non_null
        )

        working[
            column
        ] = parsed

    # ---------------------------------------------------------
    # Remove rows whose X value is missing.
    # A chart cannot position these rows.
    # ---------------------------------------------------------

    before_x_filter = len(
        working
    )

    working = working[
        working[
            request.x
        ].notna()
    ].copy()

    removed_x_rows = (
        before_x_filter
        - len(working)
    )

    if removed_x_rows > 0:
        warnings.append(
            f"{removed_x_rows} row(s) were omitted "
            f"because '{request.x}' was missing."
        )

    if working.empty:
        raise ChartBuildError(
            "No chartable rows remain after "
            "validating the x-axis values."
        )

    source_row_count = len(
        dataframe
    )

    (
        chart_dataframe,
        sampled,
    ) = _sample_dataframe(
        working,
        request.max_rows,
    )

    if sampled:
        warnings.append(
            "The dataset was downsampled for "
            "visualization performance while "
            "preserving coverage across the "
            "full dataset."
        )

    # ---------------------------------------------------------
    # Build JSON-safe chart rows.
    # ---------------------------------------------------------

    chart_data: list[
        dict[str, Any]
    ] = []

    for _, row in chart_dataframe.iterrows():
        if request.chart_type == "scatter":
            x_value = _safe_float(
                row[
                    request.x
                ]
            )
        else:
            x_value = _json_safe_value(
                row[
                    request.x
                ]
            )

        chart_row: dict[
            str,
            Any,
        ] = {
            request.x:
                x_value
        }

        for series_name in request.series:
            chart_row[
                series_name
            ] = _safe_float(
                row[
                    series_name
                ]
            )

        chart_data.append(
            chart_row
        )

    # ---------------------------------------------------------
    # Coverage represents the percentage of non-null
    # source series values that successfully became
    # chartable numeric values.
    # ---------------------------------------------------------

    if total_source_values == 0:
        source_coverage = 0.0
    else:
        source_coverage = (
            total_valid_values
            / total_source_values
        )

    source_coverage = round(
        min(
            max(
                source_coverage,
                0.0,
            ),
            1.0,
        ),
        4,
    )

    return ChartSpecResponse(
        dataset_id=metadata.dataset_id,
        file_name=metadata.file_name,
        chart_type=request.chart_type,
        title=_build_title(
            request
        ),
        x=request.x,
        series=request.series,
        data=chart_data,
        source_row_count=source_row_count,
        chart_row_count=len(
            chart_data
        ),
        sampled=sampled,
        explanation=_build_explanation(
            request
        ),
        source_coverage=source_coverage,
        warnings=warnings,
    )