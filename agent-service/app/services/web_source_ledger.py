from __future__ import annotations

import hashlib
import json

from datetime import (
    datetime,
    timezone,
)

from typing import Any

from uuid import uuid4

from supabase import (
    Client,
    create_client,
)

from app.core.config import settings

from app.schemas.web import (
    WebCitationSource,
    WebFetchedSource,
)


class WebSourceLedgerError(
    RuntimeError
):
    pass


# =========================================================
# Supabase
# =========================================================


def _supabase_client() -> Client:
    """
    Create the service-role Supabase client used for
    persistent source-ledger writes.
    """

    if not settings.supabase_url:
        raise WebSourceLedgerError(
            "SUPABASE_URL is required "
            "for web source persistence."
        )

    if not (
        settings
        .supabase_service_role_key
    ):
        raise WebSourceLedgerError(
            "SUPABASE_SERVICE_ROLE_KEY "
            "is required for web source "
            "persistence."
        )

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


# =========================================================
# Normalization / fingerprinting
# =========================================================


def _normalize_text(
    value: str | None,
) -> str:
    """
    Normalize whitespace before fingerprinting and
    persisting evidence snippets.
    """

    if not value:
        return ""

    return " ".join(
        value
        .strip()
        .split()
    )


def _normalized_retrieval_score(
    evidence_score: float | None,
) -> float | None:
    """
    Convert the Phase 3H-C deterministic web-evidence
    score into the normalized 0..1 range expected by
    source_ledger.retrieval_score.

    Current 3H-C passage scoring has a theoretical
    maximum of 150:

        query coverage   <= 100
        year bonus       <= 40
        multi-term bonus <= 10

    Example:

        raw evidence score = 125
        normalized score   = 125 / 150
                           = 0.833333...

    The raw score remains available separately in
    metadata.evidence_score and in
    WebCitationSource.evidence_score.
    """

    if evidence_score is None:
        return None

    try:
        score = float(
            evidence_score
        )

    except (
        TypeError,
        ValueError,
    ):
        return None

    normalized = (
        score / 150.0
    )

    return max(
        0.0,
        min(
            normalized,
            1.0,
        ),
    )


def _web_source_fingerprint(
    *,
    user_id: str,
    url: str,
    page_number: int | None,
    snippet: str,
) -> str:
    """
    Fingerprint the actual evidence passage rather
    than only the URL.

    This allows one web page or PDF to provide several
    independently citable passages while still
    deduplicating the same passage across repeated
    requests.
    """

    payload = {
        "user_id":
            user_id,

        "source_type":
            "web",

        "url":
            url.strip(),

        "page_number":
            page_number,

        "snippet":
            _normalize_text(
                snippet
            ),
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode(
            "utf-8"
        )
    ).hexdigest()


# =========================================================
# Supabase result helpers
# =========================================================


def _result_rows(
    response: Any,
) -> list[dict[str, Any]]:
    """
    Extract list rows from a Supabase API response.
    """

    data = getattr(
        response,
        "data",
        None,
    )

    if not isinstance(
        data,
        list,
    ):
        return []

    return [
        row
        for row in data
        if isinstance(
            row,
            dict,
        )
    ]


def _find_existing_source(
    *,
    client: Client,
    user_id: str,
    source_fingerprint: str,
) -> dict[str, Any] | None:
    """
    Find an already persisted evidence passage by
    fingerprint.
    """

    response = (
        client
        .table(
            "source_ledger"
        )
        .select(
            "*"
        )
        .eq(
            "user_id",
            user_id,
        )
        .eq(
            "source_fingerprint",
            source_fingerprint,
        )
        .limit(
            1
        )
        .execute()
    )

    rows = (
        _result_rows(
            response
        )
    )

    return (
        rows[0]
        if rows
        else None
    )


def _insert_source(
    *,
    client: Client,
    row: dict[str, Any],
) -> dict[str, Any]:
    """
    Persist a source-ledger row and return the inserted
    row.
    """

    response = (
        client
        .table(
            "source_ledger"
        )
        .insert(
            row
        )
        .execute()
    )

    rows = (
        _result_rows(
            response
        )
    )

    if not rows:
        raise WebSourceLedgerError(
            "Supabase did not return the "
            "inserted web source row."
        )

    return rows[0]


# =========================================================
# Web source persistence
# =========================================================


def _get_or_create_web_source(
    *,
    client: Client,
    user_id: str,
    fetched_source: WebFetchedSource,
    snippet: str,
    page_number: int | None,
    evidence_score: float,
    retrieved_at: str,
) -> dict[str, Any]:
    """
    Persist one verified web evidence passage.

    Existing source_ledger vocabulary is reused:

        source_title
        source_uri
        source_snippet
        retrieval_score

    Phase 3H-D adds:

        source_url
        source_domain
        retrieved_at
        trust_tier
        provider
        content_type
    """

    normalized_snippet = (
        _normalize_text(
            snippet
        )
    )

    if not normalized_snippet:
        raise WebSourceLedgerError(
            "Cannot persist an empty "
            "web evidence snippet."
        )

    fingerprint = (
        _web_source_fingerprint(
            user_id=user_id,
            url=(
                fetched_source
                .final_url
            ),
            page_number=(
                page_number
            ),
            snippet=(
                normalized_snippet
            ),
        )
    )

    # -----------------------------------------------------
    # Reuse an already persisted identical passage.
    # -----------------------------------------------------

    existing = (
        _find_existing_source(
            client=client,
            user_id=user_id,
            source_fingerprint=(
                fingerprint
            ),
        )
    )

    if existing:
        return existing

    # -----------------------------------------------------
    # Normalize the 3H-C evidence score for the generic
    # source_ledger.retrieval_score column.
    # -----------------------------------------------------

    normalized_retrieval_score = (
        _normalized_retrieval_score(
            evidence_score
        )
    )

    source_id = (
        f"source-{uuid4()}"
    )

    # -----------------------------------------------------
    # Preserve provider-specific/raw information in
    # metadata.
    #
    # retrieval_score itself remains normalized 0..1.
    # -----------------------------------------------------

    metadata = {
        "search_rank":
            fetched_source.search_rank,

        "http_status":
            fetched_source.http_status,

        "content_type":
            fetched_source.content_type,

        "trust_tier":
            fetched_source.trust_tier,

        "provider":
            "serper",

        # Raw deterministic 3H-C passage score.
        "evidence_score":
            evidence_score,

        # Normalized value written to retrieval_score.
        "normalized_retrieval_score":
            normalized_retrieval_score,

        "phase":
            "3H-D",
    }

    # -----------------------------------------------------
    # Source ledger row
    # -----------------------------------------------------

    row = {
        "id":
            source_id,

        "user_id":
            user_id,

        "source_type":
            "web",

        # Existing generic logical source identifier.
        #
        # For web evidence, the fetched canonical URL is
        # the natural source identifier.
        "source_id":
            fetched_source.final_url,

        # Web evidence does not belong to an uploaded
        # document/chunk.
        "document_id":
            None,

        "chunk_id":
            None,

        "source_fingerprint":
            fingerprint,

        # -------------------------------------------------
        # Existing source_ledger columns from Phase 3G
        # -------------------------------------------------

        "source_title":
            fetched_source.title,

        "source_uri":
            fetched_source.final_url,

        "source_snippet":
            normalized_snippet,

        "page_number":
            page_number,

        # IMPORTANT:
        # Database constraint expects normalized 0..1.
        "retrieval_score":
            normalized_retrieval_score,

        "metadata":
            metadata,

        # -------------------------------------------------
        # Phase 3H-D provenance columns
        # -------------------------------------------------

        "source_url":
            fetched_source.final_url,

        "source_domain":
            fetched_source.domain,

        "retrieved_at":
            retrieved_at,

        "trust_tier":
            fetched_source.trust_tier,

        "provider":
            "serper",

        "content_type":
            fetched_source.content_type,
    }

    try:
        return (
            _insert_source(
                client=client,
                row=row,
            )
        )

    except Exception:
        # -------------------------------------------------
        # A concurrent request may have inserted the same
        # fingerprint between our lookup and insert.
        #
        # Re-check before propagating the exception.
        # -------------------------------------------------

        existing = (
            _find_existing_source(
                client=client,
                user_id=user_id,
                source_fingerprint=(
                    fingerprint
                ),
            )
        )

        if existing:
            return existing

        raise


# =========================================================
# Public persistence service
# =========================================================


def persist_web_citation_sources(
    *,
    user_id: str,
    fetched_sources: list[
        WebFetchedSource
    ],
    first_source_number: int = 2001,
) -> list[
    WebCitationSource
]:
    """
    Persist verified Phase 3H-C evidence passages and
    convert them into request-scoped citation sources.

    Persistent identity:
        source_ledger.id

    Request-scoped citation identity:
        [Web Source 2001]
        [Web Source 2002]
        ...

    Citation numbers are deliberately not stored as the
    permanent database identity.
    """

    if first_source_number < 2001:
        raise WebSourceLedgerError(
            "Web citation source numbers "
            "must begin at 2001 or higher."
        )

    client = (
        _supabase_client()
    )

    retrieved_at = (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )

    citation_sources: list[
        WebCitationSource
    ] = []

    source_number = (
        first_source_number
    )

    # Prevent duplicate citation entries within the same
    # request if the same persisted ledger row is reached
    # more than once.
    seen_source_ids: set[str] = set()

    for fetched_source in (
        fetched_sources
    ):
        for passage in (
            fetched_source
            .evidence_passages
        ):
            snippet = (
                _normalize_text(
                    passage.text
                )
            )

            if not snippet:
                continue

            row = (
                _get_or_create_web_source(
                    client=client,
                    user_id=user_id,
                    fetched_source=(
                        fetched_source
                    ),
                    snippet=snippet,
                    page_number=(
                        passage
                        .page_number
                    ),
                    evidence_score=(
                        passage.score
                    ),
                    retrieved_at=(
                        retrieved_at
                    ),
                )
            )

            persisted_id = str(
                row.get(
                    "id",
                    "",
                )
            ).strip()

            if not persisted_id:
                raise WebSourceLedgerError(
                    "Persisted source_ledger row "
                    "did not contain an id."
                )

            if persisted_id in (
                seen_source_ids
            ):
                continue

            seen_source_ids.add(
                persisted_id
            )

            # -------------------------------------------------
            # Build request-scoped citation object.
            #
            # Prefer values returned from the database so the
            # citation reflects what was actually persisted.
            # -------------------------------------------------

            citation_title = str(
                row.get(
                    "source_title"
                )
                or fetched_source.title
            )

            citation_url = str(
                row.get(
                    "source_url"
                )
                or row.get(
                    "source_uri"
                )
                or fetched_source.final_url
            )

            citation_domain = str(
                row.get(
                    "source_domain"
                )
                or fetched_source.domain
            )

            citation_snippet = str(
                row.get(
                    "source_snippet"
                )
                or snippet
            )

            citation_page_number = (
                row.get(
                    "page_number"
                )
            )

            citation_retrieved_at = str(
                row.get(
                    "retrieved_at"
                )
                or retrieved_at
            )

            # -------------------------------------------------
            # Keep the raw web evidence score for the citation
            # object.
            #
            # Do NOT replace this with retrieval_score, because
            # retrieval_score is the normalized DB value.
            # -------------------------------------------------

            citation_sources.append(
                WebCitationSource(
                    source_number=(
                        source_number
                    ),

                    source_id=(
                        persisted_id
                    ),

                    title=(
                        citation_title
                    ),

                    url=(
                        citation_url
                    ),

                    domain=(
                        citation_domain
                    ),

                    snippet=(
                        citation_snippet
                    ),

                    page_number=(
                        citation_page_number
                    ),

                    trust_tier=(
                        fetched_source
                        .trust_tier
                    ),

                    provider=(
                        "serper"
                    ),

                    content_type=(
                        fetched_source
                        .content_type
                    ),

                    # Raw Phase 3H-C score.
                    evidence_score=(
                        passage.score
                    ),

                    retrieved_at=(
                        citation_retrieved_at
                    ),
                )
            )

            source_number += 1

    return citation_sources