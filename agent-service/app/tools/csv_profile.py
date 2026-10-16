import math
import re
from typing import Any

import pandas as pd

from app.schemas.data import (
    ChartSuggestion,
    ColumnProfile,
    DatasetProfileResponse,
    NumericSummary,
)
from app.services.csv_store import (
    load_csv_dataset,
)


NUMERIC_INFERENCE_THRESHOLD = 0.90
DATE_INFERENCE_THRESHOLD = 0.90

DATE_COLUMN_HINTS = (
    "date",
    "month",
    "year",
    "period",
    "quarter",
    "time",
)

BOOLEAN_VALUES = {
    "true",
    "false",
    "yes",
    "no",
    "y",
    "n",
}

CURRENCY_PATTERN = re.compile(
    r"[$€£¥₹]"
)


def _finite_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(
        numeric_value
    ):
        return None

    return numeric_value


def _parse_numeric_series(
    series: pd.Series,
) -> tuple[pd.Series, float, str]:
    non_null = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    if non_null.empty:
        return (
            pd.Series(
                dtype="float64"
            ),
            0.0,
            "number",
        )

    percentage_hits = (
        non_null
        .str.endswith("%")
        .sum()
    )

    currency_hits = (
        non_null
        .str.contains(
            CURRENCY_PATTERN,
            regex=True,
        )
        .sum()
    )

    cleaned = non_null.copy()

    # Accounting notation:
    # (1200) -> -1200
    cleaned = cleaned.str.replace(
        r"^\((.*)\)$",
        r"-\1",
        regex=True,
    )

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

    parsed = pd.to_numeric(
        cleaned,
        errors="coerce",
    )

    parse_ratio = float(
        parsed.notna().mean()
    )

    if (
        percentage_hits
        / len(non_null)
        >= 0.5
    ):
        numeric_format = "percentage"

    elif (
        currency_hits
        / len(non_null)
        >= 0.5
    ):
        numeric_format = "currency"

    else:
        numeric_format = "number"

    return (
        parsed,
        parse_ratio,
        numeric_format,
    )


def _date_parse_ratio(
    series: pd.Series,
) -> float:
    non_null = (
        series
        .dropna()
        .astype(str)
        .str.strip()
    )

    if non_null.empty:
        return 0.0

    try:
        parsed = pd.to_datetime(
            non_null,
            errors="coerce",
        )
    except Exception:
        return 0.0

    return float(
        parsed.notna().mean()
    )


def _looks_like_date_column(
    column_name: str,
) -> bool:
    lowered = column_name.lower()

    return any(
        hint in lowered
        for hint in DATE_COLUMN_HINTS
    )


def _is_boolean_series(
    series: pd.Series,
) -> bool:
    non_null = (
        series
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
    )

    if non_null.empty:
        return False

    unique_values = set(
        non_null.unique()
    )

    return (
        bool(unique_values)
        and unique_values.issubset(
            BOOLEAN_VALUES
        )
    )


def _numeric_summary(
    parsed: pd.Series,
) -> NumericSummary | None:
    numeric = (
        parsed
        .dropna()
        .astype(float)
    )

    if numeric.empty:
        return None

    return NumericSummary(
        min=_finite_float(
            numeric.min()
        ),
        max=_finite_float(
            numeric.max()
        ),
        mean=_finite_float(
            numeric.mean()
        ),
        median=_finite_float(
            numeric.median()
        ),
        std=_finite_float(
            numeric.std()
        ),
        q1=_finite_float(
            numeric.quantile(0.25)
        ),
        q3=_finite_float(
            numeric.quantile(0.75)
        ),
        sum=_finite_float(
            numeric.sum()
        ),
    )


def _example_values(
    series: pd.Series,
    limit: int = 3,
) -> list[Any]:
    values = (
        series
        .dropna()
        .head(limit)
        .tolist()
    )

    return [
        str(value)
        for value in values
    ]


def _profile_column(
    *,
    column_name: str,
    series: pd.Series,
    row_count: int,
) -> ColumnProfile:
    missing_count = int(
        series.isna().sum()
    )

    non_null_count = int(
        series.notna().sum()
    )

    missing_percent = (
        round(
            (
                missing_count
                / row_count
                * 100
            ),
            2,
        )
        if row_count
        else 0.0
    )

    unique_count = int(
        series.nunique(
            dropna=True
        )
    )

    examples = _example_values(
        series
    )

    if _is_boolean_series(
        series
    ):
        return ColumnProfile(
            name=column_name,
            inferred_type="boolean",
            non_null_count=non_null_count,
            missing_count=missing_count,
            missing_percent=missing_percent,
            unique_count=unique_count,
            example_values=examples,
        )

    # Columns whose names strongly imply time/date
    # are checked for dates before numeric inference.
    if _looks_like_date_column(
        column_name
    ):
        date_ratio = _date_parse_ratio(
            series
        )

        if (
            date_ratio
            >= DATE_INFERENCE_THRESHOLD
        ):
            return ColumnProfile(
                name=column_name,
                inferred_type="date",
                non_null_count=non_null_count,
                missing_count=missing_count,
                missing_percent=missing_percent,
                unique_count=unique_count,
                example_values=examples,
            )

    (
        parsed_numeric,
        numeric_ratio,
        numeric_format,
    ) = _parse_numeric_series(
        series
    )

    if (
        numeric_ratio
        >= NUMERIC_INFERENCE_THRESHOLD
    ):
        return ColumnProfile(
            name=column_name,
            inferred_type="numeric",
            non_null_count=non_null_count,
            missing_count=missing_count,
            missing_percent=missing_percent,
            unique_count=unique_count,
            numeric_format=numeric_format,
            numeric_summary=_numeric_summary(
                parsed_numeric
            ),
            example_values=examples,
        )

    date_ratio = _date_parse_ratio(
        series
    )

    if (
        date_ratio
        >= DATE_INFERENCE_THRESHOLD
    ):
        return ColumnProfile(
            name=column_name,
            inferred_type="date",
            non_null_count=non_null_count,
            missing_count=missing_count,
            missing_percent=missing_percent,
            unique_count=unique_count,
            example_values=examples,
        )

    return ColumnProfile(
        name=column_name,
        inferred_type="string",
        non_null_count=non_null_count,
        missing_count=missing_count,
        missing_percent=missing_percent,
        unique_count=unique_count,
        example_values=examples,
    )


def _suggest_charts(
    *,
    profiles: list[ColumnProfile],
) -> list[ChartSuggestion]:
    suggestions: list[
        ChartSuggestion
    ] = []

    date_columns = [
        profile.name
        for profile in profiles
        if profile.inferred_type
        == "date"
    ]

    numeric_columns = [
        profile.name
        for profile in profiles
        if profile.inferred_type
        == "numeric"
    ]

    categorical_columns = [
        profile.name
        for profile in profiles
        if profile.inferred_type
        in {
            "string",
            "boolean",
        }
    ]

    if (
        date_columns
        and numeric_columns
    ):
        suggestions.append(
            ChartSuggestion(
                chart_type="line",
                x=date_columns[0],
                series=numeric_columns[:4],
                reason=(
                    "A date/time column and "
                    "numeric columns were detected, "
                    "which is suitable for trend analysis."
                ),
            )
        )

    if (
        categorical_columns
        and numeric_columns
    ):
        suggestions.append(
            ChartSuggestion(
                chart_type="bar",
                x=categorical_columns[0],
                series=numeric_columns[:3],
                reason=(
                    "A categorical column and "
                    "numeric columns were detected, "
                    "which is suitable for comparisons."
                ),
            )
        )

    if len(
        numeric_columns
    ) >= 2:
        suggestions.append(
            ChartSuggestion(
                chart_type="scatter",
                x=numeric_columns[0],
                series=[
                    numeric_columns[1]
                ],
                reason=(
                    "Multiple numeric columns were "
                    "detected, which can be used "
                    "to inspect relationships."
                ),
            )
        )

    if not suggestions:
        suggestions.append(
            ChartSuggestion(
                chart_type="table",
                x=None,
                series=[],
                reason=(
                    "No strong chart pattern was "
                    "detected. A table view is the "
                    "safest initial representation."
                ),
            )
        )

    return suggestions


def _sample_rows(
    dataframe: pd.DataFrame,
    limit: int = 10,
) -> list[dict[str, Any]]:
    sample = dataframe.head(
        limit
    ).copy()

    sample = sample.where(
        pd.notna(sample),
        None,
    )

    rows = sample.to_dict(
        orient="records"
    )

    return [
        {
            str(key): value
            for key, value
            in row.items()
        }
        for row in rows
    ]


def profile_csv_dataset(
    *,
    dataset_id: str,
    user_id: str,
) -> DatasetProfileResponse:
    (
        metadata,
        dataframe,
    ) = load_csv_dataset(
        dataset_id=dataset_id,
        user_id=user_id,
    )

    row_count = len(
        dataframe
    )

    profiles = [
        _profile_column(
            column_name=str(
                column_name
            ),
            series=dataframe[
                column_name
            ],
            row_count=row_count,
        )
        for column_name
        in dataframe.columns
    ]

    return DatasetProfileResponse(
        dataset_id=metadata.dataset_id,
        file_name=metadata.file_name,
        row_count=metadata.row_count,
        column_count=metadata.column_count,
        columns=profiles,
        sample_rows=_sample_rows(
            dataframe
        ),
        chart_suggestions=_suggest_charts(
            profiles=profiles
        ),
    )