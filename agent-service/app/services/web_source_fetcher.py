from __future__ import annotations

import io
import re

from dataclasses import dataclass

from urllib.parse import (
    urlparse,
)

from bs4 import BeautifulSoup

from pypdf import PdfReader

from app.core.config import settings

from app.schemas.web import (
    WebEvidencePassage,
    WebFetchedSource,
    WebFetchFailure,
    WebSearchCandidate,
)

from app.services.safe_web_fetch import (
    WebFetchError,
    fetch_public_resource,
)


YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._&-]*"
)


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "did",
    "do",
    "does",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "with",
}


@dataclass
class ExtractedWebDocument:
    title: str | None

    # page_number is None for HTML/text.
    pages: list[
        tuple[
            int | None,
            str,
        ]
    ]

    warnings: list[str]


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def _clean_text(
    value: str,
) -> str:
    lines = []

    for raw_line in (
        value
        .replace(
            "\r\n",
            "\n",
        )
        .replace(
            "\r",
            "\n",
        )
        .split(
            "\n"
        )
    ):
        line = " ".join(
            raw_line
            .strip()
            .split()
        )

        if line:
            lines.append(
                line
            )

    return "\n".join(
        lines
    )


def _domain_from_url(
    url: str,
) -> str:
    return (
        urlparse(
            url
        )
        .netloc
        .lower()
        .removeprefix(
            "www."
        )
    )


def _domains_related(
    first: str,
    second: str,
) -> bool:
    first = (
        first
        .lower()
        .removeprefix(
            "www."
        )
    )

    second = (
        second
        .lower()
        .removeprefix(
            "www."
        )
    )

    return (
        first == second
        or first.endswith(
            "." + second
        )
        or second.endswith(
            "." + first
        )
    )


# ---------------------------------------------------------
# HTML
# ---------------------------------------------------------


def _extract_html(
    content: bytes,
) -> ExtractedWebDocument:
    soup = BeautifulSoup(
        content,
        "html.parser",
    )

    title: str | None = None

    if soup.title:
        title_value = (
            soup.title.get_text(
                " ",
                strip=True,
            )
        )

        if title_value:
            title = (
                " ".join(
                    title_value.split()
                )
            )

    # Remove code / navigation / decorative content.
    for tag in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "template",
            "svg",
            "canvas",
            "form",
            "nav",
            "footer",
            "aside",
        ]
    ):
        tag.decompose()

    root = (
        soup.find(
            "main"
        )
        or soup.find(
            "article"
        )
        or soup.body
        or soup
    )

    text = root.get_text(
        "\n",
        strip=True,
    )

    text = _clean_text(
        text
    )

    text = text[
        :
        settings
        .web_fetch_max_text_chars
    ]

    return ExtractedWebDocument(
        title=title,
        pages=[
            (
                None,
                text,
            )
        ],
        warnings=[],
    )


# ---------------------------------------------------------
# Plain text
# ---------------------------------------------------------


def _extract_plain_text(
    content: bytes,
) -> ExtractedWebDocument:
    text = content.decode(
        "utf-8",
        errors="replace",
    )

    text = _clean_text(
        text
    )

    text = text[
        :
        settings
        .web_fetch_max_text_chars
    ]

    return ExtractedWebDocument(
        title=None,
        pages=[
            (
                None,
                text,
            )
        ],
        warnings=[],
    )


# ---------------------------------------------------------
# PDF
# ---------------------------------------------------------


def _extract_pdf(
    content: bytes,
) -> ExtractedWebDocument:
    warnings: list[str] = []

    try:
        reader = PdfReader(
            io.BytesIO(
                content
            ),
            strict=False,
        )

    except Exception as error:
        raise WebFetchError(
            (
                "Unable to parse PDF: "
                f"{type(error).__name__}: "
                f"{error}"
            )
        ) from error

    title: str | None = None

    try:
        metadata = (
            reader.metadata
        )

        if (
            metadata
            and metadata.title
        ):
            title = (
                " ".join(
                    str(
                        metadata.title
                    )
                    .split()
                )
            )

    except Exception:
        title = None

    total_pages = len(
        reader.pages
    )

    page_limit = min(
        total_pages,
        settings
        .web_fetch_max_pdf_pages,
    )

    if total_pages > page_limit:
        warnings.append(
            (
                "PDF contained "
                f"{total_pages} pages; "
                f"only the first "
                f"{page_limit} were "
                "processed."
            )
        )

    extracted_pages: list[
        tuple[
            int | None,
            str,
        ]
    ] = []

    remaining_chars = (
        settings
        .web_fetch_max_text_chars
    )

    for page_index in range(
        page_limit
    ):
        if remaining_chars <= 0:
            warnings.append(
                (
                    "PDF text extraction "
                    "reached the configured "
                    "text limit."
                )
            )

            break

        page = (
            reader.pages[
                page_index
            ]
        )

        try:
            page_text = (
                page.extract_text()
                or ""
            )

        except Exception as error:
            warnings.append(
                (
                    "Unable to extract "
                    f"PDF page "
                    f"{page_index + 1}: "
                    f"{type(error).__name__}"
                )
            )

            continue

        page_text = _clean_text(
            page_text
        )

        if not page_text:
            continue

        if len(
            page_text
        ) > remaining_chars:
            page_text = (
                page_text[
                    :
                    remaining_chars
                ]
            )

        extracted_pages.append(
            (
                page_index + 1,
                page_text,
            )
        )

        remaining_chars -= len(
            page_text
        )

    if not extracted_pages:
        raise WebFetchError(
            (
                "PDF was fetched but no "
                "usable text could be "
                "extracted."
            )
        )

    return ExtractedWebDocument(
        title=title,
        pages=extracted_pages,
        warnings=warnings,
    )


# ---------------------------------------------------------
# Evidence passage generation
# ---------------------------------------------------------


def _query_terms(
    query: str,
) -> list[str]:
    output: list[str] = []

    seen: set[str] = set()

    for match in (
        TOKEN_PATTERN.findall(
            query.lower()
        )
    ):
        token = (
            match
            .strip(
                "._-&"
            )
        )

        if not token:
            continue

        is_year = bool(
            YEAR_PATTERN.fullmatch(
                token
            )
        )

        if (
            not is_year
            and (
                len(token) < 3
                or token
                in STOP_WORDS
            )
        ):
            continue

        if token in seen:
            continue

        seen.add(
            token
        )

        output.append(
            token
        )

    return output


def _chunk_text(
    *,
    text: str,
    page_number: int | None,
) -> list[
    tuple[
        int | None,
        str,
    ]
]:
    max_chars = (
        settings
        .web_evidence_passage_chars
    )

    lines = [
        line.strip()
        for line
        in text.split(
            "\n"
        )
        if line.strip()
    ]

    chunks: list[
        tuple[
            int | None,
            str,
        ]
    ] = []

    current: list[str] = []

    current_length = 0

    def flush() -> None:
        nonlocal current
        nonlocal current_length

        if not current:
            return

        chunks.append(
            (
                page_number,
                " ".join(
                    current
                ),
            )
        )

        current = []

        current_length = 0

    for line in lines:
        # Handle single huge lines.
        while len(
            line
        ) > max_chars:
            flush()

            chunks.append(
                (
                    page_number,
                    line[
                        :
                        max_chars
                    ],
                )
            )

            line = line[
                max_chars:
            ]

        projected = (
            current_length
            + len(
                line
            )
            + 1
        )

        if (
            current
            and projected
            > max_chars
        ):
            flush()

        current.append(
            line
        )

        current_length += (
            len(
                line
            )
            + 1
        )

    flush()

    return chunks


def _score_passage(
    *,
    passage: str,
    terms: list[str],
) -> tuple[
    float,
    list[str],
]:
    lowered = (
        passage.lower()
    )

    passage_tokens = set(
        TOKEN_PATTERN.findall(
            lowered
        )
    )

    matched = [
        term
        for term
        in terms
        if term
        in passage_tokens
    ]

    if not matched:
        return (
            0.0,
            [],
        )

    coverage = (
        len(
            matched
        )
        / max(
            len(
                terms
            ),
            1,
        )
    )

    query_years = {
        term
        for term
        in terms
        if YEAR_PATTERN.fullmatch(
            term
        )
    }

    matched_years = (
        query_years
        .intersection(
            matched
        )
    )

    year_bonus = (
        40.0
        * (
            len(
                matched_years
            )
            / max(
                len(
                    query_years
                ),
                1,
            )
        )
        if query_years
        else 0.0
    )

    multi_term_bonus = (
        10.0
        if len(
            matched
        ) >= 2
        else 0.0
    )

    score = (
        coverage
        * 100.0
        + year_bonus
        + multi_term_bonus
    )

    return (
        round(
            score,
            4,
        ),
        matched,
    )


def _extract_evidence(
    *,
    query: str,
    document: ExtractedWebDocument,
) -> list[
    WebEvidencePassage
]:
    terms = _query_terms(
        query
    )

    if not terms:
        return []

    scored: list[
        WebEvidencePassage
    ] = []

    for (
        page_number,
        page_text,
    ) in document.pages:

        chunks = _chunk_text(
            text=page_text,
            page_number=(
                page_number
            ),
        )

        for (
            chunk_page,
            chunk,
        ) in chunks:

            (
                score,
                matched_terms,
            ) = _score_passage(
                passage=chunk,
                terms=terms,
            )

            if score <= 0:
                continue

            scored.append(
                WebEvidencePassage(
                    text=chunk,
                    score=score,
                    page_number=(
                        chunk_page
                    ),
                    matched_terms=(
                        matched_terms
                    ),
                )
            )

    scored.sort(
        key=lambda item:
            item.score,
        reverse=True,
    )

    return scored[
        :
        settings
        .web_evidence_passages_per_source
    ]


# ---------------------------------------------------------
# Candidate fetch ordering
# ---------------------------------------------------------


def _candidate_fetch_score(
    *,
    query: str,
    candidate: WebSearchCandidate,
) -> float:
    terms = _query_terms(
        query
    )

    haystack = " ".join(
        [
            candidate.title,
            candidate.snippet
            or "",
            candidate.url,
        ]
    ).lower()

    haystack_tokens = set(
        TOKEN_PATTERN.findall(
            haystack
        )
    )

    matched = [
        term
        for term
        in terms
        if term
        in haystack_tokens
    ]

    coverage = (
        len(
            matched
        )
        / max(
            len(
                terms
            ),
            1,
        )
    )

    requested_years = {
        term
        for term
        in terms
        if YEAR_PATTERN.fullmatch(
            term
        )
    }

    year_bonus = 0.0

    if requested_years:
        if (
            requested_years
            .intersection(
                haystack_tokens
            )
        ):
            year_bonus = 30.0

        else:
            year_bonus = -15.0

    return (
        candidate.ranking_score
        + (
            coverage
            * 50.0
        )
        + year_bonus
    )


# ---------------------------------------------------------
# Public service
# ---------------------------------------------------------


def fetch_candidate_sources(
    *,
    query: str,
    candidates: list[
        WebSearchCandidate
    ],
) -> tuple[
    list[
        WebFetchedSource
    ],
    list[
        WebFetchFailure
    ],
]:
    fetched_sources: list[
        WebFetchedSource
    ] = []

    failures: list[
        WebFetchFailure
    ] = []

    ranked_candidates = sorted(
        candidates,
        key=lambda candidate:
            _candidate_fetch_score(
                query=query,
                candidate=candidate,
            ),
        reverse=True,
    )

    attempts = 0

    evidence_sources = 0

    for candidate in (
        ranked_candidates
    ):
        if (
            attempts
            >= settings
            .web_fetch_max_candidates
        ):
            break

        # Do not fetch known low-trust discovery
        # candidates in the finance MVP.
        if (
            candidate.trust_tier
            == "low_trust"
        ):
            continue

        attempts += 1

        try:
            raw = (
                fetch_public_resource(
                    candidate.url
                )
            )

            if (
                raw.content_kind
                == "html"
            ):
                document = (
                    _extract_html(
                        raw.content
                    )
                )

            elif (
                raw.content_kind
                == "text"
            ):
                document = (
                    _extract_plain_text(
                        raw.content
                    )
                )

            elif (
                raw.content_kind
                == "pdf"
            ):
                document = (
                    _extract_pdf(
                        raw.content
                    )
                )

            else:
                raise WebFetchError(
                    (
                        "Unsupported extracted "
                        "content kind."
                    )
                )

            evidence = (
                _extract_evidence(
                    query=query,
                    document=document,
                )
            )

            final_domain = (
                _domain_from_url(
                    raw.final_url
                )
            )

            warnings = list(
                document.warnings
            )

            effective_trust = (
                candidate.trust_tier
            )

            if not _domains_related(
                candidate.domain,
                final_domain,
            ):
                warnings.append(
                    (
                        "Source redirected to "
                        "a different domain; "
                        "search-result trust "
                        "classification was "
                        "downgraded."
                    )
                )

                effective_trust = (
                    "general_web"
                )

            title = (
                document.title
                or candidate.title
            )

            text_chars = sum(
                len(
                    page_text
                )
                for (
                    _page_number,
                    page_text,
                )
                in document.pages
            )

            fetched_sources.append(
                WebFetchedSource(
                    search_rank=(
                        candidate.rank
                    ),
                    title=title,
                    requested_url=(
                        candidate.url
                    ),
                    final_url=(
                        raw.final_url
                    ),
                    domain=(
                        final_domain
                    ),
                    content_type=(
                        raw.content_kind
                    ),
                    trust_tier=(
                        effective_trust
                    ),
                    http_status=(
                        raw.status_code
                    ),
                    text_chars=(
                        text_chars
                    ),
                    evidence_passages=(
                        evidence
                    ),
                    warnings=warnings,
                )
            )

            if evidence:
                evidence_sources += 1

            if (
                evidence_sources
                >= settings
                .web_fetch_target_sources
            ):
                break

        except Exception as error:
            failures.append(
                WebFetchFailure(
                    search_rank=(
                        candidate.rank
                    ),
                    title=(
                        candidate.title
                    ),
                    url=(
                        candidate.url
                    ),
                    reason=(
                        f"{type(error).__name__}: "
                        f"{error}"
                    ),
                )
            )

    return (
        fetched_sources,
        failures,
    )