from __future__ import annotations

import calendar
import re

from dataclasses import dataclass, field
from datetime import (
    date,
    datetime,
    timedelta,
    timezone,
)
from decimal import (
    Decimal,
    InvalidOperation,
)
from typing import Any

from supabase import (
    Client,
    create_client,
)

from app.core.config import (
    settings,
)

from app.schemas.facts import (
    FactValidationStatus,
    FactValueType,
    FinancialFactValidationResponse,
    FinancialFactValidationResult,
)


# ============================================================
# Constants
# ============================================================


VALIDATION_THRESHOLD = 0.72


SCALE_MULTIPLIERS: dict[
    str,
    Decimal,
] = {
    "thousand":
        Decimal("1000"),

    "million":
        Decimal("1000000"),

    "billion":
        Decimal("1000000000"),

    "trillion":
        Decimal("1000000000000"),
}


MONTH_PATTERN = (
    r"(January|February|March|April|May|June|"
    r"July|August|September|October|November|December)"
)


FULL_DATE_PATTERN = (
    rf"{MONTH_PATTERN}"
    r"\s+(\d{1,2}),\s*(\d{4})"
)


NUMERIC_TOKEN_PATTERN = re.compile(
    r"""
    \(?
    \s*
    [-−]?
    \s*
    (?:
        US\$
        |
        C\$
        |
        A\$
        |
        [$€£]
    )?
    \s*
    \d[\d,]*
    (?:\.\d+)?
    \s*
    %?
    \s*
    \)?
    """,
    re.VERBOSE
    | re.IGNORECASE,
)


# ============================================================
# Errors
# ============================================================


class FactValidationError(
    RuntimeError,
):
    pass


# ============================================================
# Internal models
# ============================================================


@dataclass
class PeriodNormalization:
    start: date | None = None

    end: date | None = None

    year: int | None = None

    kind: str | None = None


@dataclass
class FactAssessment:
    fact_row: dict[str, Any]

    source_row: (
        dict[str, Any]
        | None
    )

    source_text: str

    canonical_metric_key: str

    status: FactValidationStatus

    score: float

    reason: str

    normalized_numeric_value: (
        Decimal | None
    )

    normalization_multiplier: (
        Decimal | None
    )

    currency: str | None

    scale: str | None

    period_start: date | None

    period_end: date | None

    period_key: str

    details: dict[
        str,
        Any,
    ] = field(
        default_factory=dict,
    )

    warnings: list[str] = field(
        default_factory=list,
    )


# ============================================================
# Supabase
# ============================================================


def _get_supabase_client() -> Client:
    if not settings.supabase_url:
        raise FactValidationError(
            "SUPABASE_URL is required "
            "for fact validation."
        )

    if (
        not settings
        .supabase_service_role_key
    ):
        raise FactValidationError(
            "SUPABASE_SERVICE_ROLE_KEY "
            "is required for fact validation."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


# ============================================================
# Generic normalization helpers
# ============================================================


def _clean_text(
    value: str | None,
) -> str:
    if not value:
        return ""

    return " ".join(
        value
        .strip()
        .split()
    )

def _normalized_words(
    value: str | None,
) -> str:
    value = value or ""

    value = (
        value
        .lower()
        .replace(
            "\u00a0",
            " ",
        )
        .replace(
            "\u00ad",
            "",
        )
    )

    # Repair PDF line-break / extraction hyphenation.
    #
    # Examples:
    #   "Consoli- dated" -> "consolidated"
    #   "non- operating" -> "nonoperating"
    #   "equity- based" -> "equitybased"
    value = re.sub(
        r"(?<=[a-z])-\s+(?=[a-z])",
        "",
        value,
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )
def _compact_text(
    value: str | None,
) -> str:
    value = (
        value
        or ""
    )

    value = (
        value
        .lower()
        .replace(
            "\u00a0",
            " ",
        )
    )

    value = re.sub(
        r"\s+",
        "",
        value,
    )

    return value


def _normalize_metric_key(
    value: str,
) -> str:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "_",
        value
        .strip()
        .lower(),
    )

    return (
        normalized
        .strip("_")
        [:300]
    )


def _metric_base_key(
    value: str,
) -> str:
    """
    The LLM may emit:

        revenue
        revenue_2
        revenue_3

    when parsing adjacent table columns.

    We do NOT blindly strip suffixes globally.
    Group-level logic below only canonicalizes
    them when the human-readable metric label
    is also the same.
    """

    return re.sub(
        r"_\d+$",
        "",
        value,
    )


def _as_decimal(
    value: Any,
) -> Decimal | None:
    if (
        value is None
        or value == ""
    ):
        return None

    try:
        return Decimal(
            str(value)
        )

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return None


def _decimal_equal(
    left: Decimal,
    right: Decimal,
) -> bool:
    difference = abs(
        left - right
    )

    tolerance = max(
        Decimal("0.000001"),
        abs(left)
        * Decimal("0.000001"),
        abs(right)
        * Decimal("0.000001"),
    )

    return (
        difference
        <= tolerance
    )


# ============================================================
# Numeric parsing
# ============================================================


def _parse_raw_numeric_value(
    raw_value: str | None,
) -> Decimal | None:
    if not raw_value:
        return None

    value = (
        raw_value
        .strip()
        .replace(
            "\u2212",
            "-",
        )
        .replace(
            "−",
            "-",
        )
    )

    accounting_negative = (
        value.startswith("(")
        and value.endswith(")")
    )

    value = re.sub(
        r"(?i)\b("
        r"usd|eur|gbp|cad|aud|jpy|chf|"
        r"thousand|thousands|"
        r"million|millions|"
        r"billion|billions|"
        r"trillion|trillions"
        r")\b",
        "",
        value,
    )

    value = (
        value
        .replace(
            ",",
            "",
        )
        .replace(
            "%",
            "",
        )
    )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value,
    )

    if not match:
        return None

    try:
        parsed = Decimal(
            match.group(0)
        )

    except InvalidOperation:
        return None

    if (
        accounting_negative
        and parsed > 0
    ):
        parsed = -parsed

    return parsed


def _raw_value_exact_match(
    *,
    raw_value: str,
    source_text: str,
) -> bool:
    raw = _compact_text(
        raw_value
    )

    source = _compact_text(
        source_text
    )

    if not raw:
        return False

    return raw in source


def _numeric_value_in_source(
    *,
    value: Decimal,
    source_text: str,
) -> bool:
    for match in (
        NUMERIC_TOKEN_PATTERN
        .finditer(
            source_text
        )
    ):
        parsed = (
            _parse_raw_numeric_value(
                match.group(0)
            )
        )

        if (
            parsed is not None
            and _decimal_equal(
                parsed,
                value,
            )
        ):
            return True

    return False


# ============================================================
# Scale normalization
# ============================================================


def _normalize_scale(
    value: str | None,
) -> str | None:
    normalized = (
        _normalized_words(
            value
        )
    )

    aliases = {
        "thousand":
            "thousand",

        "thousands":
            "thousand",

        "million":
            "million",

        "millions":
            "million",

        "billion":
            "billion",

        "billions":
            "billion",

        "trillion":
            "trillion",

        "trillions":
            "trillion",
    }

    return aliases.get(
        normalized
    )


def _scale_from_raw(
    raw_value: str,
) -> str | None:
    normalized = (
        _normalized_words(
            raw_value
        )
    )

    for candidate in (
        "trillion",
        "billion",
        "million",
        "thousand",
    ):
        if (
            candidate
            in normalized.split()
            or (
                candidate + "s"
                in normalized.split()
            )
        ):
            return candidate

    return None


def _scale_from_source(
    source_text: str,
) -> str | None:
    normalized = (
        _normalized_words(
            source_text
        )
    )

    found: set[str] = set()

    patterns = {
        "thousand": (
            r"\bin thousands\b",
            r"\bdollars in thousands\b",
            r"\bamounts in thousands\b",
        ),

        "million": (
            r"\bin millions\b",
            r"\bdollars in millions\b",
            r"\bamounts in millions\b",
        ),

        "billion": (
            r"\bin billions\b",
            r"\bdollars in billions\b",
            r"\bamounts in billions\b",
        ),

        "trillion": (
            r"\bin trillions\b",
            r"\bdollars in trillions\b",
            r"\bamounts in trillions\b",
        ),
    }

    for (
        scale,
        expressions,
    ) in patterns.items():
        if any(
            re.search(
                expression,
                normalized,
            )
            for expression
            in expressions
        ):
            found.add(
                scale
            )

    if len(found) == 1:
        return next(
            iter(found)
        )

    return None


def _infer_scale(
    *,
    raw_value: str,
    source_text: str,
    existing_scale: str | None,
) -> tuple[
    str | None,
    str,
]:
    raw_scale = (
        _scale_from_raw(
            raw_value
        )
    )

    if raw_scale:
        return (
            raw_scale,
            "raw_value",
        )

    normalized_existing = (
        _normalize_scale(
            existing_scale
        )
    )

    if (
        normalized_existing
        and (
            normalized_existing
            in _normalized_words(
                source_text
            ).split()
        )
    ):
        return (
            normalized_existing,
            "existing_supported_by_source",
        )

    source_scale = (
        _scale_from_source(
            source_text
        )
    )

    if source_scale:
        return (
            source_scale,
            "source_context",
        )

    return (
        None,
        "unknown",
    )


# ============================================================
# Currency normalization
# ============================================================


def _infer_currency(
    *,
    raw_value: str,
    source_text: str,
    existing_currency: str | None,
    unit_label: str | None,
) -> tuple[
    str | None,
    str,
]:
    combined = (
        f"{raw_value}\n"
        f"{unit_label or ''}\n"
        f"{source_text}"
    )

    normalized = (
        combined.lower()
    )

    patterns: list[
        tuple[
            str,
            tuple[str, ...],
        ]
    ] = [
        (
            "USD",
            (
                r"\busd\b",
                r"\bu\.s\.\s*dollars?\b",
                r"\bus\s+dollars?\b",
                r"\bus\$",
            ),
        ),
        (
            "EUR",
            (
                r"\beur\b",
                r"€",
                r"\beuros?\b",
            ),
        ),
        (
            "GBP",
            (
                r"\bgbp\b",
                r"£",
                r"\bpounds?\s+sterling\b",
            ),
        ),
        (
            "CAD",
            (
                r"\bcad\b",
                r"\bc\$",
                r"\bcanadian dollars?\b",
            ),
        ),
        (
            "AUD",
            (
                r"\baud\b",
                r"\ba\$",
                r"\baustralian dollars?\b",
            ),
        ),
        (
            "JPY",
            (
                r"\bjpy\b",
                r"\bjapanese yen\b",
            ),
        ),
        (
            "CHF",
            (
                r"\bchf\b",
                r"\bswiss francs?\b",
            ),
        ),
    ]

    detected: set[str] = set()

    for (
        currency,
        expressions,
    ) in patterns:
        if any(
            re.search(
                expression,
                normalized,
            )
            for expression
            in expressions
        ):
            detected.add(
                currency
            )

    if len(detected) == 1:
        return (
            next(
                iter(detected)
            ),
            "source",
        )

    existing = (
        existing_currency
        .strip()
        .upper()
        if existing_currency
        else None
    )

    if (
        existing
        and existing
        in detected
    ):
        return (
            existing,
            "existing_supported_by_source",
        )

    # A bare "$" is deliberately NOT mapped to USD.
    # It could represent USD, CAD, AUD, etc.
    return (
        None,
        "unknown",
    )


# ============================================================
# Period normalization
# ============================================================


def _parse_date_match(
    match: re.Match[str],
) -> date | None:
    try:
        month_name = (
            match.group(1)
        )

        day = int(
            match.group(2)
        )

        year = int(
            match.group(3)
        )

        return datetime.strptime(
            (
                f"{month_name} "
                f"{day}, {year}"
            ),
            "%B %d, %Y",
        ).date()

    except (
        ValueError,
        TypeError,
    ):
        return None


def _shift_months(
    value: date,
    months: int,
) -> date:
    absolute_month = (
        value.year * 12
        + value.month
        - 1
        + months
    )

    year = (
        absolute_month
        // 12
    )

    month = (
        absolute_month
        % 12
        + 1
    )

    day = min(
        value.day,
        calendar.monthrange(
            year,
            month,
        )[1],
    )

    return date(
        year,
        month,
        day,
    )


def _normalize_period(
    period_label: str | None,
) -> PeriodNormalization:
    if not period_label:
        return PeriodNormalization()

    cleaned = _clean_text(
        period_label
    )

    # --------------------------------------------
    # N months ended
    # --------------------------------------------

    month_duration_pattern = re.compile(
        rf"(?i)\b"
        r"(three|six|nine|twelve)"
        r"\s+months?\s+ended\s+"
        + FULL_DATE_PATTERN
    )

    match = (
        month_duration_pattern
        .search(
            cleaned
        )
    )

    if match:
        count_map = {
            "three": 3,
            "six": 6,
            "nine": 9,
            "twelve": 12,
        }

        months = count_map[
            match.group(1).lower()
        ]

        synthetic_match = re.match(
            FULL_DATE_PATTERN,
            (
                f"{match.group(2)} "
                f"{match.group(3)}, "
                f"{match.group(4)}"
            ),
        )

        if synthetic_match:
            end = _parse_date_match(
                synthetic_match
            )

            if end:
                start = (
                    _shift_months(
                        end,
                        -months,
                    )
                    + timedelta(
                        days=1
                    )
                )

                return (
                    PeriodNormalization(
                        start=start,
                        end=end,
                        year=end.year,
                        kind=(
                            f"{months}_months_ended"
                        ),
                    )
                )

    # --------------------------------------------
    # Quarter ended
    # --------------------------------------------

    quarter_pattern = re.compile(
        rf"(?i)\bquarter\s+ended\s+"
        + FULL_DATE_PATTERN
    )

    match = quarter_pattern.search(
        cleaned
    )

    if match:
        end = _parse_date_match(
            match
        )

        if end:
            start = (
                _shift_months(
                    end,
                    -3,
                )
                + timedelta(
                    days=1
                )
            )

            return PeriodNormalization(
                start=start,
                end=end,
                year=end.year,
                kind="quarter_ended",
            )

    # --------------------------------------------
    # Year ended
    # --------------------------------------------

    year_pattern = re.compile(
        rf"(?i)\b"
        r"(?:year|fiscal year)"
        r"\s+ended\s+"
        + FULL_DATE_PATTERN
    )

    match = year_pattern.search(
        cleaned
    )

    if match:
        end = _parse_date_match(
            match
        )

        if end:
            start = (
                _shift_months(
                    end,
                    -12,
                )
                + timedelta(
                    days=1
                )
            )

            return PeriodNormalization(
                start=start,
                end=end,
                year=end.year,
                kind="year_ended",
            )

    # --------------------------------------------
    # Point-in-time date
    # --------------------------------------------

    direct_date = re.search(
        FULL_DATE_PATTERN,
        cleaned,
        re.IGNORECASE,
    )

    if direct_date:
        parsed = _parse_date_match(
            direct_date
        )

        if parsed:
            return PeriodNormalization(
                start=parsed,
                end=parsed,
                year=parsed.year,
                kind="point_in_time",
            )

    # --------------------------------------------
    # FY2024 / FY 2024
    #
    # We retain the year for sorting but do not
    # manufacture calendar dates because fiscal
    # years do not necessarily end December 31.
    # --------------------------------------------

    fiscal_match = re.search(
        r"(?i)\bFY\s*(20\d{2})\b",
        cleaned,
    )

    if fiscal_match:
        return PeriodNormalization(
            year=int(
                fiscal_match.group(1)
            ),
            kind="fiscal_year_label",
        )

    # --------------------------------------------
    # Bare year
    # --------------------------------------------

    if re.fullmatch(
        r"20\d{2}",
        cleaned,
    ):
        return PeriodNormalization(
            year=int(
                cleaned
            ),
            kind="year_label",
        )

    return PeriodNormalization()


def _period_key(
    *,
    period_label: str | None,
    normalized: PeriodNormalization,
) -> str:
    if (
        normalized.start
        and normalized.end
    ):
        return (
            f"{normalized.start.isoformat()}"
            f"/"
            f"{normalized.end.isoformat()}"
        )

    if normalized.year:
        return (
            f"year:{normalized.year}"
        )

    return _normalized_words(
        period_label
    )


# ============================================================
# Evidence helpers
# ============================================================




def _metric_label_in_source(
    *,
    metric_label: str,
    source_text: str,
) -> bool:
    metric = (
        _normalized_words(
            metric_label
        )
    )

    source = (
        _normalized_words(
            source_text
        )
    )

    if not metric:
        return False

    # Best case: full normalized label appears.
    if metric in source:
        return True

    metric_tokens = [
        token
        for token in metric.split()
        if len(token) >= 3
    ]

    if not metric_tokens:
        return False

    source_tokens = set(
        source.split()
    )

    matched = sum(
        1
        for token in metric_tokens
        if token in source_tokens
    )

    coverage = (
        matched
        / len(metric_tokens)
    )

    # Financial table labels are frequently damaged by
    # PDF extraction. Require strong token overlap rather
    # than literal identity.
    return coverage >= 0.75

def _period_in_source(
    *,
    period_label: str | None,
    source_text: str,
) -> bool:
    if not period_label:
        return False

    period = (
        _normalized_words(
            period_label
        )
    )

    source = (
        _normalized_words(
            source_text
        )
    )

    if (
        period
        and period in source
    ):
        return True

    years = re.findall(
        r"\b20\d{2}\b",
        period_label,
    )

    if (
        years
        and all(
            year in source_text
            for year in years
        )
    ):
        return True

    return False


# ============================================================
# Data loading
# ============================================================


def _load_fact_rows(
    *,
    client: Client,
    user_id: str,
    document_id: str,
    revalidate: bool,
) -> list[
    dict[str, Any]
]:
    query = (
        client
        .table(
            "analysis_facts"
        )
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
    )

    if not revalidate:
        query = query.eq(
            "validation_status",
            (
                FactValidationStatus
                .pending
                .value
            ),
        )

    response = (
        query
        .order(
            "created_at"
        )
        .execute()
    )

    return (
        response.data
        or []
    )


def _load_sources(
    *,
    client: Client,
    user_id: str,
    source_ids: list[str],
) -> dict[
    str,
    dict[str, Any],
]:
    if not source_ids:
        return {}

    response = (
        client
        .table(
            "source_ledger"
        )
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .in_(
            "id",
            source_ids,
        )
        .execute()
    )

    return {
        row["id"]: row
        for row
        in (
            response.data
            or []
        )
    }


def _load_chunks(
    *,
    client: Client,
    user_id: str,
    document_id: str,
    chunk_ids: list[str],
) -> dict[
    str,
    str,
]:
    if not chunk_ids:
        return {}

    response = (
        client
        .table(
            "rag_chunks"
        )
        .select(
            "id,text"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "document_id",
            document_id,
        )
        .in_(
            "id",
            chunk_ids,
        )
        .execute()
    )

    return {
        row["id"]:
            str(
                row.get(
                    "text",
                    "",
                )
            )
        for row
        in (
            response.data
            or []
        )
    }


# ============================================================
# Individual validation
# ============================================================


def _assess_fact(
    *,
    fact_row: dict[str, Any],
    source_row: dict[str, Any] | None,
    source_text: str,
) -> FactAssessment:
    metric_key = (
        _normalize_metric_key(
            str(
                fact_row.get(
                    "metric_key",
                    "",
                )
            )
        )
    )

    metric_label = str(
        fact_row.get(
            "metric_label",
            "",
        )
    )

    raw_value = str(
        fact_row.get(
            "raw_value",
            "",
        )
    )

    value_type = str(
        fact_row.get(
            "value_type",
            "",
        )
    )

    numeric_value = (
        _as_decimal(
            fact_row.get(
                "numeric_value"
            )
        )
    )

    warnings: list[str] = []

    details: dict[
        str,
        Any,
    ] = {}

    # --------------------------------------------
    # Source integrity
    # --------------------------------------------

    if source_row is None:
        return FactAssessment(
            fact_row=fact_row,
            source_row=None,
            source_text="",
            canonical_metric_key=(
                metric_key
            ),
            status=(
                FactValidationStatus
                .rejected
            ),
            score=0.0,
            reason=(
                "Source ledger entry "
                "was not found."
            ),
            normalized_numeric_value=None,
            normalization_multiplier=None,
            currency=None,
            scale=None,
            period_start=None,
            period_end=None,
            period_key="",
            details={
                "source_found": False,
            },
        )

    if (
        source_row.get(
            "document_id"
        )
        != fact_row.get(
            "document_id"
        )
    ):
        return FactAssessment(
            fact_row=fact_row,
            source_row=source_row,
            source_text=source_text,
            canonical_metric_key=(
                metric_key
            ),
            status=(
                FactValidationStatus
                .rejected
            ),
            score=0.0,
            reason=(
                "Fact document_id does not "
                "match source document_id."
            ),
            normalized_numeric_value=None,
            normalization_multiplier=None,
            currency=None,
            scale=None,
            period_start=None,
            period_end=None,
            period_key="",
            details={
                "source_found": True,
                "document_match": False,
            },
        )

    # --------------------------------------------
    # Evidence
    # --------------------------------------------

    raw_exact = (
        _raw_value_exact_match(
            raw_value=raw_value,
            source_text=source_text,
        )
    )

    raw_parsed = (
        _parse_raw_numeric_value(
            raw_value
        )
    )

    numeric_consistent = False

    numeric_in_source = False

    if (
        numeric_value is not None
        and raw_parsed is not None
    ):
        numeric_consistent = (
            _decimal_equal(
                numeric_value,
                raw_parsed,
            )
        )

        numeric_in_source = (
            _numeric_value_in_source(
                value=numeric_value,
                source_text=source_text,
            )
        )

    metric_found = (
        _metric_label_in_source(
            metric_label=(
                metric_label
            ),
            source_text=(
                source_text
            ),
        )
    )

    period_label = (
        fact_row.get(
            "period_label"
        )
    )

    period_found = (
        _period_in_source(
            period_label=(
                period_label
            ),
            source_text=(
                source_text
            ),
        )
    )

    details.update(
        {
            "source_found":
                True,

            "document_match":
                True,

            "raw_value_exact_match":
                raw_exact,

            "raw_value_parsed":
                (
                    str(
                        raw_parsed
                    )
                    if (
                        raw_parsed
                        is not None
                    )
                    else None
                ),

            "numeric_value_matches_raw":
                numeric_consistent,

            "numeric_value_found_in_source":
                numeric_in_source,

            "metric_label_found_in_source":
                metric_found,

            "period_found_in_source":
                period_found,
        }
    )

    # --------------------------------------------
    # Text facts
    # --------------------------------------------

    if (
        value_type
        == FactValueType
        .text
        .value
    ):
        text_value = str(
            fact_row.get(
                "text_value",
                "",
            )
        )

        text_found = (
            _compact_text(
                text_value
            )
            in _compact_text(
                source_text
            )
        )

        score = (
            0.70
            if text_found
            else 0.0
        )

        if metric_found:
            score += 0.15

        if period_found:
            score += 0.10

        score = min(
            score,
            1.0,
        )

        status = (
            FactValidationStatus
            .validated
            if (
                text_found
                and score
                >= VALIDATION_THRESHOLD
            )
            else FactValidationStatus
            .rejected
        )

        period = (
            _normalize_period(
                period_label
            )
        )

        details[
            "text_value_found_in_source"
        ] = text_found

        details[
            "period_kind"
        ] = period.kind

        details[
            "period_year"
        ] = period.year

        return FactAssessment(
            fact_row=fact_row,
            source_row=source_row,
            source_text=source_text,
            canonical_metric_key=(
                metric_key
            ),
            status=status,
            score=score,
            reason=(
                "Text fact is supported "
                "by source evidence."
                if (
                    status
                    == FactValidationStatus
                    .validated
                )
                else (
                    "Text value was not "
                    "found in source evidence."
                )
            ),
            normalized_numeric_value=None,
            normalization_multiplier=None,
            currency=None,
            scale=None,
            period_start=period.start,
            period_end=period.end,
            period_key=(
                _period_key(
                    period_label=(
                        period_label
                    ),
                    normalized=(
                        period
                    ),
                )
            ),
            details=details,
            warnings=warnings,
        )

    # --------------------------------------------
    # Quantitative hard checks
    # --------------------------------------------

    if numeric_value is None:
        return FactAssessment(
            fact_row=fact_row,
            source_row=source_row,
            source_text=source_text,
            canonical_metric_key=metric_key,
            status=(
                FactValidationStatus
                .rejected
            ),
            score=0.0,
            reason=(
                "Quantitative fact does not "
                "contain numeric_value."
            ),
            normalized_numeric_value=None,
            normalization_multiplier=None,
            currency=None,
            scale=None,
            period_start=None,
            period_end=None,
            period_key="",
            details=details,
            warnings=warnings,
        )

    if raw_parsed is None:
        return FactAssessment(
            fact_row=fact_row,
            source_row=source_row,
            source_text=source_text,
            canonical_metric_key=metric_key,
            status=(
                FactValidationStatus
                .rejected
            ),
            score=0.0,
            reason=(
                "raw_value could not be "
                "parsed deterministically."
            ),
            normalized_numeric_value=None,
            normalization_multiplier=None,
            currency=None,
            scale=None,
            period_start=None,
            period_end=None,
            period_key="",
            details=details,
            warnings=warnings,
        )

    if not numeric_consistent:
        return FactAssessment(
            fact_row=fact_row,
            source_row=source_row,
            source_text=source_text,
            canonical_metric_key=metric_key,
            status=(
                FactValidationStatus
                .rejected
            ),
            score=0.0,
            reason=(
                "numeric_value does not "
                "match raw_value."
            ),
            normalized_numeric_value=None,
            normalization_multiplier=None,
            currency=None,
            scale=None,
            period_start=None,
            period_end=None,
            period_key="",
            details=details,
            warnings=warnings,
        )

    if not (
        raw_exact
        or numeric_in_source
    ):
        return FactAssessment(
            fact_row=fact_row,
            source_row=source_row,
            source_text=source_text,
            canonical_metric_key=metric_key,
            status=(
                FactValidationStatus
                .rejected
            ),
            score=0.0,
            reason=(
                "Neither raw_value nor its "
                "numeric equivalent was found "
                "in source evidence."
            ),
            normalized_numeric_value=None,
            normalization_multiplier=None,
            currency=None,
            scale=None,
            period_start=None,
            period_end=None,
            period_key="",
            details=details,
            warnings=warnings,
        )

    

    # --------------------------------------------
    # Scale
    # --------------------------------------------

    (
        scale,
        scale_source,
    ) = _infer_scale(
        raw_value=raw_value,
        source_text=source_text,
        existing_scale=(
            fact_row.get(
                "scale"
            )
        ),
    )

    multiplier = (
        SCALE_MULTIPLIERS.get(
            scale,
            Decimal("1"),
        )
    )

    apply_scale = (
        value_type
        not in {
            FactValueType
            .percentage
            .value,

            FactValueType
            .ratio
            .value,

            FactValueType
            .per_share
            .value,
        }
    )

    if not apply_scale:
        multiplier = (
            Decimal("1")
        )

    normalized_numeric_value = (
        numeric_value
        * multiplier
    )

    # --------------------------------------------
    # Currency
    # --------------------------------------------

    (
        currency,
        currency_source,
    ) = _infer_currency(
        raw_value=raw_value,
        source_text=source_text,
        existing_currency=(
            fact_row.get(
                "currency"
            )
        ),
        unit_label=(
            fact_row.get(
                "unit_label"
            )
        ),
    )

    # --------------------------------------------
    # Period
    # --------------------------------------------

    period = (
        _normalize_period(
            period_label
        )
    )

    period_key = (
        _period_key(
            period_label=(
                period_label
            ),
            normalized=(
                period
            ),
        )
    )

    # --------------------------------------------
    # Validation score
    #
    # Model confidence is deliberately a very
    # small component. Evidence dominates.
    # --------------------------------------------

    score = 0.0

    if raw_exact:
        score += 0.35

    elif numeric_in_source:
        score += 0.22

    if numeric_consistent:
        score += 0.30

    if metric_found:
        score += 0.15

    if period_found:
        score += 0.10

    retrieval_score = (
        float(
            source_row.get(
                "retrieval_score"
            )
            or 0.0
        )
    )

    retrieval_score = max(
        0.0,
        min(
            1.0,
            retrieval_score,
        ),
    )

    score += (
        retrieval_score
        * 0.05
    )

    model_confidence = float(
        fact_row.get(
            "confidence"
        )
        or 0.0
    )

    model_confidence = max(
        0.0,
        min(
            1.0,
            model_confidence,
        ),
    )

    score += (
        model_confidence
        * 0.05
    )

    score = min(
        score,
        1.0,
    )

    if score >= VALIDATION_THRESHOLD:
        status = (
            FactValidationStatus
            .validated
        )

        reason = (
            "Fact passed deterministic "
            "source and numeric validation."
        )

    else:
        status = (
            FactValidationStatus
            .rejected
        )

        reason = (
            "Fact evidence was insufficient "
            "to meet the deterministic "
            "validation threshold."
        )

    details.update(
        {
            "scale_source":
                scale_source,

            "currency_source":
                currency_source,

            "period_kind":
                period.kind,

            "period_year":
                period.year,

            "model_confidence":
                model_confidence,

            "retrieval_score":
                retrieval_score,

            "validation_threshold":
                VALIDATION_THRESHOLD,
        }
    )

    if (
        period_label
        and not (
            period.start
            or period.end
            or period.year
        )
    ):
        warnings.append(
            "Period label could not be "
            "normalized deterministically."
        )

    if (
        value_type
        == FactValueType
        .currency
        .value
        and currency is None
    ):
        warnings.append(
            "Currency could not be "
            "established unambiguously."
        )

    return FactAssessment(
        fact_row=fact_row,
        source_row=source_row,
        source_text=source_text,
        canonical_metric_key=metric_key,
        status=status,
        score=score,
        reason=reason,
        normalized_numeric_value=(
            normalized_numeric_value
        ),
        normalization_multiplier=(
            multiplier
        ),
        currency=currency,
        scale=scale,
        period_start=(
            period.start
        ),
        period_end=(
            period.end
        ),
        period_key=(
            period_key
        ),
        details=details,
        warnings=warnings,
    )


# ============================================================
# Canonical metric keys
# ============================================================


def _canonicalize_metric_keys(
    assessments: list[
        FactAssessment
    ],
) -> None:
    groups: dict[
        str,
        list[
            FactAssessment
        ],
    ] = {}

    for assessment in assessments:
        label_key = (
            _normalized_words(
                assessment
                .fact_row
                .get(
                    "metric_label"
                )
            )
        )

        if not label_key:
            continue

        groups.setdefault(
            label_key,
            [],
        ).append(
            assessment
        )

    for group in groups.values():
        if len(group) < 2:
            continue

        base_keys = {
            _metric_base_key(
                assessment
                .canonical_metric_key
            )
            for assessment
            in group
        }

        if len(base_keys) != 1:
            continue

        canonical = next(
            iter(base_keys)
        )

        for assessment in group:
            assessment.canonical_metric_key = (
                canonical
            )

            assessment.details[
                "canonicalized_from_metric_key"
            ] = (
                assessment
                .fact_row
                .get(
                    "metric_key"
                )
            )


# ============================================================
# Duplicate / conflict detection
# ============================================================


def _identity_key(
    assessment: FactAssessment,
) -> tuple[
    str,
    ...,
]:
    row = (
        assessment.fact_row
    )

    return (
        _normalized_words(
            row.get(
                "company"
            )
        ),

        assessment
        .canonical_metric_key,

        assessment
        .period_key,

        _normalized_words(
            row.get(
                "category"
            )
        ),

        _normalized_words(
            row.get(
                "statement_type"
            )
        ),
    )


def _value_signature(
    assessment: FactAssessment,
) -> tuple[
    str,
    ...,
]:
    row = (
        assessment.fact_row
    )

    value = (
        str(
            assessment
            .normalized_numeric_value
        )
        if (
            assessment
            .normalized_numeric_value
            is not None
        )
        else _clean_text(
            row.get(
                "text_value"
            )
        )
    )

    return (
        value,

        _clean_text(
            row.get(
                "value_type"
            )
        ),

        _normalized_words(
            row.get(
                "unit_key"
            )
        ),

        assessment.currency or "",

        assessment.scale or "",
    )


def _apply_duplicate_and_conflict_rules(
    assessments: list[
        FactAssessment
    ],
) -> None:
    groups: dict[
        tuple[str, ...],
        list[
            FactAssessment
        ],
    ] = {}

    for assessment in assessments:
        if (
            assessment.status
            == FactValidationStatus
            .rejected
        ):
            continue

        groups.setdefault(
            _identity_key(
                assessment
            ),
            [],
        ).append(
            assessment
        )

    for (
        identity,
        group,
    ) in groups.items():
        if len(group) < 2:
            continue

        signatures = {
            _value_signature(
                assessment
            )
            for assessment
            in group
        }

        # ----------------------------------------
        # Same metric + same period + same value
        # => duplicate.
        # Keep the strongest evidence.
        # ----------------------------------------

        if len(signatures) == 1:
            ordered = sorted(
                group,
                key=lambda item: (
                    item.score,
                    float(
                        (
                            item
                            .source_row
                            or {}
                        ).get(
                            "retrieval_score"
                        )
                        or 0.0
                    ),
                ),
                reverse=True,
            )

            keeper = (
                ordered[0]
            )

            for duplicate in (
                ordered[1:]
            ):
                duplicate.status = (
                    FactValidationStatus
                    .rejected
                )

                duplicate.reason = (
                    "Duplicate of validated "
                    f"fact {keeper.fact_row['id']}."
                )

                duplicate.details[
                    "duplicate_of_fact_id"
                ] = (
                    keeper
                    .fact_row[
                        "id"
                    ]
                )

            continue

        # ----------------------------------------
        # Same canonical identity but differing
        # values => conflict.
        #
        # This is especially important for the
        # `_2` / `_3` table-column behavior when
        # the extractor could not recover periods.
        # ----------------------------------------

        fact_ids = [
            str(
                assessment
                .fact_row[
                    "id"
                ]
            )
            for assessment
            in group
        ]

        for assessment in group:
            assessment.status = (
                FactValidationStatus
                .conflict
            )

            if not (
                assessment.period_key
            ):
                assessment.reason = (
                    "Multiple values were "
                    "extracted for the same "
                    "canonical metric without "
                    "a distinguishable period."
                )

            else:
                assessment.reason = (
                    "Conflicting values were "
                    "extracted for the same "
                    "canonical metric and period."
                )

            assessment.details[
                "conflicting_fact_ids"
            ] = [
                fact_id
                for fact_id
                in fact_ids
                if (
                    fact_id
                    != str(
                        assessment
                        .fact_row[
                            "id"
                        ]
                    )
                )
            ]


# ============================================================
# Persistence
# ============================================================


def _update_assessment(
    *,
    client: Client,
    user_id: str,
    assessment: FactAssessment,
) -> None:
    payload: dict[
        str,
        Any,
    ] = {
        "canonical_metric_key":
            assessment
            .canonical_metric_key,

        "normalized_numeric_value":
            (
                str(
                    assessment
                    .normalized_numeric_value
                )
                if (
                    assessment
                    .normalized_numeric_value
                    is not None
                )
                else None
            ),

        "normalization_multiplier":
            (
                str(
                    assessment
                    .normalization_multiplier
                )
                if (
                    assessment
                    .normalization_multiplier
                    is not None
                )
                else None
            ),

        "currency":
            assessment.currency,

        "scale":
            assessment.scale,

        "period_start":
            (
                assessment
                .period_start
                .isoformat()
                if (
                    assessment
                    .period_start
                )
                else None
            ),

        "period_end":
            (
                assessment
                .period_end
                .isoformat()
                if (
                    assessment
                    .period_end
                )
                else None
            ),

        "validation_status":
            assessment
            .status
            .value,

        "validation_score":
            assessment.score,

        "validation_reason":
            assessment.reason,

        "validation_details":
            assessment.details,

        "validated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),
    }

    response = (
        client
        .table(
            "analysis_facts"
        )
        .update(
            payload
        )
        .eq(
            "id",
            assessment
            .fact_row[
                "id"
            ],
        )
        .eq(
            "user_id",
            user_id,
        )
        .execute()
    )

    if not (
        response.data
        or []
    ):
        raise FactValidationError(
            "Fact validation update "
            "returned no row for "
            f"{assessment.fact_row['id']}."
        )


# ============================================================
# Public API
# ============================================================


def validate_document_facts(
    *,
    user_id: str,
    document_id: str,
    revalidate: bool = False,
) -> FinancialFactValidationResponse:
    client = (
        _get_supabase_client()
    )

    fact_rows = (
        _load_fact_rows(
            client=client,
            user_id=user_id,
            document_id=document_id,
            revalidate=revalidate,
        )
    )

    if not fact_rows:
        return (
            FinancialFactValidationResponse(
                document_id=(
                    document_id
                ),
                processed_count=0,
                validated_count=0,
                rejected_count=0,
                conflict_count=0,
                results=[],
                warnings=[
                    (
                        "No pending facts were "
                        "found for this document."
                    )
                ],
            )
        )

    source_ids = list(
        {
            str(
                row[
                    "source_ledger_id"
                ]
            )
            for row
            in fact_rows
            if row.get(
                "source_ledger_id"
            )
        }
    )

    source_map = (
        _load_sources(
            client=client,
            user_id=user_id,
            source_ids=source_ids,
        )
    )

    chunk_ids = list(
        {
            str(
                source[
                    "chunk_id"
                ]
            )
            for source
            in source_map.values()
            if source.get(
                "chunk_id"
            )
        }
    )

    chunk_map = (
        _load_chunks(
            client=client,
            user_id=user_id,
            document_id=document_id,
            chunk_ids=chunk_ids,
        )
    )

    assessments: list[
        FactAssessment
    ] = []

    for fact_row in fact_rows:
        source = (
            source_map.get(
                str(
                    fact_row.get(
                        "source_ledger_id"
                    )
                )
            )
        )

        source_text = ""

        if source:
            chunk_id = (
                source.get(
                    "chunk_id"
                )
            )

            if chunk_id:
                source_text = (
                    chunk_map.get(
                        str(
                            chunk_id
                        ),
                        "",
                    )
                )

            if not source_text:
                source_text = str(
                    source.get(
                        "source_snippet",
                        "",
                    )
                )

        assessments.append(
            _assess_fact(
                fact_row=(
                    fact_row
                ),
                source_row=(
                    source
                ),
                source_text=(
                    source_text
                ),
            )
        )

    # Fix model-generated revenue_2/revenue_3 style
    # keys only when labels demonstrate that they refer
    # to the same conceptual metric.
    _canonicalize_metric_keys(
        assessments
    )

    # Detect duplicated evidence and conflicting values.
    _apply_duplicate_and_conflict_rules(
        assessments
    )

    persistence_warnings: list[
        str
    ] = []

    for assessment in assessments:
        try:
            _update_assessment(
                client=client,
                user_id=user_id,
                assessment=(
                    assessment
                ),
            )

        except Exception as error:
            persistence_warnings.append(
                (
                    "Failed to persist "
                    f"validation for "
                    f"{assessment.fact_row['id']}: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

    results = [
        FinancialFactValidationResult(
            fact_id=str(
                assessment
                .fact_row[
                    "id"
                ]
            ),

            metric_key=str(
                assessment
                .fact_row.get(
                    "metric_key",
                    "",
                )
            ),

            canonical_metric_key=(
                assessment
                .canonical_metric_key
            ),

            status=(
                assessment.status
            ),

            validation_score=(
                assessment.score
            ),

            reason=(
                assessment.reason
            ),

            normalized_numeric_value=(
                assessment
                .normalized_numeric_value
            ),

            normalization_multiplier=(
                assessment
                .normalization_multiplier
            ),

            currency=(
                assessment.currency
            ),

            scale=(
                assessment.scale
            ),

            period_start=(
                assessment
                .period_start
            ),

            period_end=(
                assessment
                .period_end
            ),

            warnings=(
                assessment.warnings
            ),
        )
        for assessment
        in assessments
    ]

    validated_count = sum(
        1
        for assessment
        in assessments
        if (
            assessment.status
            == FactValidationStatus
            .validated
        )
    )

    rejected_count = sum(
        1
        for assessment
        in assessments
        if (
            assessment.status
            == FactValidationStatus
            .rejected
        )
    )

    conflict_count = sum(
        1
        for assessment
        in assessments
        if (
            assessment.status
            == FactValidationStatus
            .conflict
        )
    )

    return (
        FinancialFactValidationResponse(
            document_id=(
                document_id
            ),

            processed_count=(
                len(
                    assessments
                )
            ),

            validated_count=(
                validated_count
            ),

            rejected_count=(
                rejected_count
            ),

            conflict_count=(
                conflict_count
            ),

            results=(
                results
            ),

            warnings=(
                persistence_warnings
            ),
        )
    )


# ============================================================
# Phase 3H-E
# Web financial fact validation
# ============================================================


def validate_web_facts(
    *,
    user_id: str,
    fact_ids: list[str],
    revalidate: bool = False,
):
    """
    Validate structured facts derived from persisted
    web evidence.

    The actual deterministic evidence assessment is the
    same implementation used for document facts.

    Web facts differ only in loading:
    - document_id is None
    - source_type must be web
    - source text comes from source_ledger.source_snippet
    """

    from app.schemas.web import (
        WebFactValidationResponse,
        WebFactValidationResult,
    )

    if not fact_ids:
        return WebFactValidationResponse(
            processed_count=0,
            validated_count=0,
            rejected_count=0,
            conflict_count=0,
            results=[],
        )

    client = (
        _get_supabase_client()
    )

    query = (
        client
        .table(
            "analysis_facts"
        )
        .select("*")
        .eq(
            "user_id",
            user_id,
        )
        .in_(
            "id",
            fact_ids,
        )
    )

    if not revalidate:
        query = query.eq(
            "validation_status",
            (
                FactValidationStatus
                .pending
                .value
            ),
        )

    response = (
        query
        .order(
            "created_at"
        )
        .execute()
    )

    fact_rows = (
        response.data
        or []
    )

    if not fact_rows:
        return WebFactValidationResponse(
            processed_count=0,
            validated_count=0,
            rejected_count=0,
            conflict_count=0,
            results=[],
            warnings=[
                (
                    "No pending structured "
                    "web facts were found."
                )
            ],
        )

    source_ids = list(
        {
            str(
                row[
                    "source_ledger_id"
                ]
            )
            for row
            in fact_rows
            if row.get(
                "source_ledger_id"
            )
        }
    )

    source_map = (
        _load_sources(
            client=client,
            user_id=user_id,
            source_ids=source_ids,
        )
    )

    assessments: list[
        FactAssessment
    ] = []

    for fact_row in fact_rows:
        source = (
            source_map.get(
                str(
                    fact_row.get(
                        "source_ledger_id"
                    )
                )
            )
        )

        source_text = ""

        if source:
            source_text = str(
                source.get(
                    "source_snippet",
                    "",
                )
            )

        assessment = (
            _assess_fact(
                fact_row=fact_row,
                source_row=source,
                source_text=source_text,
            )
        )

        # ------------------------------------------------
        # Web-specific source integrity check
        # ------------------------------------------------

        if (
            source
            and source.get(
                "source_type"
            )
            != "web"
        ):
            assessment.status = (
                FactValidationStatus
                .rejected
            )

            assessment.score = 0.0

            assessment.reason = (
                "Structured web fact was not "
                "linked to a web source ledger "
                "entry."
            )

            assessment.details[
                "source_type_match"
            ] = False

        else:
            assessment.details[
                "source_type_match"
            ] = True

            assessment.details[
                "source_type"
            ] = "web"

        assessments.append(
            assessment
        )

    # Use the same canonicalization rules as 3G-C.
    _canonicalize_metric_keys(
        assessments
    )

    # Detect duplicate/conflicting web facts in
    # the current extraction batch.
    _apply_duplicate_and_conflict_rules(
        assessments
    )

    persistence_warnings: list[
        str
    ] = []

    for assessment in assessments:
        try:
            _update_assessment(
                client=client,
                user_id=user_id,
                assessment=assessment,
            )

        except Exception as error:
            persistence_warnings.append(
                (
                    "Unable to persist web "
                    "fact validation for "
                    f"{assessment.fact_row['id']}: "
                    f"{type(error).__name__}: "
                    f"{error}"
                )
            )

    results = [
        WebFactValidationResult(
            fact_id=(
                str(
                    assessment
                    .fact_row[
                        "id"
                    ]
                )
            ),

            metric_key=(
                str(
                    assessment
                    .fact_row.get(
                        "metric_key",
                        "",
                    )
                )
            ),

            canonical_metric_key=(
                assessment
                .canonical_metric_key
            ),

            status=(
                assessment.status
            ),

            validation_score=(
                assessment.score
            ),

            reason=(
                assessment.reason
            ),

            warnings=list(
                assessment.warnings
            ),
        )
        for assessment
        in assessments
    ]

    validated_count = sum(
        1
        for assessment
        in assessments
        if (
            assessment.status
            == FactValidationStatus
            .validated
        )
    )

    rejected_count = sum(
        1
        for assessment
        in assessments
        if (
            assessment.status
            == FactValidationStatus
            .rejected
        )
    )

    conflict_count = sum(
        1
        for assessment
        in assessments
        if (
            assessment.status
            == FactValidationStatus
            .conflict
        )
    )

    return WebFactValidationResponse(
        processed_count=len(
            assessments
        ),

        validated_count=(
            validated_count
        ),

        rejected_count=(
            rejected_count
        ),

        conflict_count=(
            conflict_count
        ),

        results=results,

        warnings=(
            persistence_warnings
        ),
    )