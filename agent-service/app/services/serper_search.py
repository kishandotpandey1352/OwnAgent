from __future__ import annotations

import json

from typing import Any

from urllib.error import (
    HTTPError,
    URLError,
)

from urllib.parse import (
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse,
)

from urllib.request import (
    Request,
    urlopen,
)

from app.core.config import settings

from app.schemas.web import (
    WebResearchInput,
    WebResearchOutput,
    WebSearchCandidate,
)


class SerperSearchError(
    RuntimeError,
):
    pass


# ---------------------------------------------------------
# Known high-trust public financial authorities.
#
# This list is intentionally small.
#
# 3H-C will introduce stronger source verification.
# ---------------------------------------------------------

PUBLIC_AUTHORITY_DOMAINS = (
    "sec.gov",
    "fca.org.uk",
    "finra.org",
    "federalreserve.gov",
    "fdic.gov",
    "occ.treas.gov",
    "bankofengland.co.uk",
    "ecb.europa.eu",
    "esma.europa.eu",
    "asic.gov.au",
)


LOW_TRUST_DOMAINS = (
    "reddit.com",
    "quora.com",
    "wikipedia.org",
)


FINANCE_SOURCE_SIGNALS = (
    "investor relations",
    "annual report",
    "annual reports",
    "10-k",
    "10-q",
    "20-f",
    "financial results",
    "quarterly results",
    "earnings release",
    "earnings report",
    "press release",
    "investors",
    "filing",
    "filings",
)


# ---------------------------------------------------------
# Text helpers
# ---------------------------------------------------------


def _clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return " ".join(
        str(value)
        .strip()
        .split()
    )


def _normalize_domain(
    value: str,
) -> str:
    value = (
        value
        .strip()
        .lower()
    )

    if "://" in value:
        value = (
            urlparse(
                value
            )
            .netloc
        )

    value = (
        value
        .split(
            "/",
            1,
        )[0]
        .removeprefix(
            "www."
        )
    )

    return value


def _domain_from_url(
    value: str,
) -> str:
    return (
        urlparse(
            value
        )
        .netloc
        .lower()
        .removeprefix(
            "www."
        )
    )


def _domain_matches(
    domain: str,
    expected: str,
) -> bool:
    domain = (
        _normalize_domain(
            domain
        )
    )

    expected = (
        _normalize_domain(
            expected
        )
    )

    return (
        domain == expected
        or domain.endswith(
            "." + expected
        )
    )


def _canonical_url(
    value: str,
) -> str:
    """
    Remove common tracking parameters so repeated
    Serper results can be deduplicated.
    """

    parsed = (
        urlparse(
            value
        )
    )

    query_items = []

    for (
        key,
        item_value,
    ) in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):
        lowered = (
            key.lower()
        )

        if lowered.startswith(
            "utm_"
        ):
            continue

        if lowered in {
            "gclid",
            "fbclid",
        }:
            continue

        query_items.append(
            (
                key,
                item_value,
            )
        )

    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            "",
            urlencode(
                query_items
            ),
            "",
        )
    )


# ---------------------------------------------------------
# Source classification
# ---------------------------------------------------------


def _is_public_authority(
    domain: str,
) -> bool:
    for trusted in (
        PUBLIC_AUTHORITY_DOMAINS
    ):
        if _domain_matches(
            domain,
            trusted,
        ):
            return True

    # Government domains get a trust boost, but this
    # does NOT yet mean the result has been verified
    # as financial evidence.
    if domain.endswith(
        ".gov"
    ):
        return True

    return False


def _is_user_trusted_domain(
    *,
    domain: str,
    trusted_domains: list[str],
) -> bool:
    for trusted in (
        trusted_domains
    ):
        if _domain_matches(
            domain,
            trusted,
        ):
            return True

    return False


def _is_low_trust(
    domain: str,
) -> bool:
    for blocked in (
        LOW_TRUST_DOMAINS
    ):
        if _domain_matches(
            domain,
            blocked,
        ):
            return True

    return False


def _has_finance_signal(
    *,
    title: str,
    snippet: str,
    url: str,
) -> bool:
    text = " ".join(
        [
            title,
            snippet,
            url,
        ]
    ).lower()

    return any(
        signal in text
        for signal
        in FINANCE_SOURCE_SIGNALS
    )


def _classify_candidate(
    *,
    domain: str,
    title: str,
    snippet: str,
    url: str,
    trusted_domains: list[str],
) -> tuple[
    str,
    float,
]:
    """
    Ranking only.

    This does NOT certify that a page contains
    correct financial evidence.

    3H-C will fetch and verify the page.
    """

    if _is_public_authority(
        domain
    ):
        return (
            "public_authority",
            100.0,
        )

    if _is_user_trusted_domain(
        domain=domain,
        trusted_domains=(
            trusted_domains
        ),
    ):
        return (
            "trusted_domain",
            90.0,
        )

    if _is_low_trust(
        domain
    ):
        return (
            "low_trust",
            10.0,
        )

    if _has_finance_signal(
        title=title,
        snippet=snippet,
        url=url,
    ):
        return (
            "finance_candidate",
            70.0,
        )

    return (
        "general_web",
        50.0,
    )


# ---------------------------------------------------------
# Serper HTTP request
# ---------------------------------------------------------


def _request_serper(
    *,
    query: str,
    num_results: int,
) -> dict[str, Any]:
    if not (
        settings
        .serper_search_enabled
    ):
        raise SerperSearchError(
            "Serper search is disabled."
        )

    if not settings.serper_api_key:
        raise SerperSearchError(
            "SERPER_API_KEY is required."
        )

    payload: dict[
        str,
        Any,
    ] = {
        "q": query,
        "num": min(
            max(
                num_results,
                1,
            ),
            20,
        ),
    }

    language = (
        settings
        .serper_language
        .strip()
    )

    if language:
        payload["hl"] = (
            language
        )

    encoded_body = (
        json.dumps(
            payload
        )
        .encode(
            "utf-8"
        )
    )

    request = Request(
        settings.serper_search_url,
        data=encoded_body,
        method="POST",
        headers={
            "X-API-KEY":
                settings.serper_api_key,

            "Content-Type":
                "application/json",

            "Accept":
                "application/json",
        },
    )

    try:
        with urlopen(
            request,
            timeout=(
                settings
                .serper_timeout_seconds
            ),
        ) as response:
            raw = (
                response
                .read()
                .decode(
                    "utf-8"
                )
            )

    except HTTPError as error:
        try:
            error_body = (
                error
                .read()
                .decode(
                    "utf-8"
                )
            )

        except Exception:
            error_body = ""

        if error.code == 401:
            raise SerperSearchError(
                (
                    "Serper returned 401 Unauthorized. "
                    "The configured API key was not accepted. "
                    f"Response: {error_body[:500]}"
                )
            ) from error


        if error.code == 403:
            raise SerperSearchError(
                (
                    "Serper returned 403 Forbidden. "
                    "The request reached Serper, but the "
                    "account or API key was not permitted "
                    "to perform this search. "
                    f"Response: {error_body[:500]}"
                )
            ) from error

        if error.code == 429:
            raise SerperSearchError(
                (
                    "Serper rate limit or "
                    "credit limit was reached."
                )
            ) from error

        raise SerperSearchError(
            (
                "Serper returned HTTP "
                f"{error.code}: "
                f"{error_body[:500]}"
            )
        ) from error

    except URLError as error:
        raise SerperSearchError(
            (
                "Unable to reach Serper: "
                f"{error}"
            )
        ) from error

    except TimeoutError as error:
        raise SerperSearchError(
            "Serper search timed out."
        ) from error

    try:
        parsed = json.loads(
            raw
        )

    except json.JSONDecodeError as error:
        raise SerperSearchError(
            (
                "Serper returned invalid "
                "JSON."
            )
        ) from error

    if not isinstance(
        parsed,
        dict,
    ):
        raise SerperSearchError(
            (
                "Serper returned an "
                "unexpected response."
            )
        )

    return parsed


# ---------------------------------------------------------
# Candidate conversion
# ---------------------------------------------------------


def _build_candidates(
    *,
    payload: dict[
        str,
        Any,
    ],
    trusted_domains: list[str],
    max_results: int,
) -> list[
    WebSearchCandidate
]:
    organic = (
        payload.get(
            "organic"
        )
        or []
    )

    ranked_candidates: list[
        tuple[
            float,
            int,
            WebSearchCandidate,
        ]
    ] = []

    seen_urls: set[str] = set()

    for index, item in enumerate(
        organic
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        title = _clean_text(
            item.get(
                "title"
            )
        )

        url = _clean_text(
            item.get(
                "link"
            )
        )

        snippet = _clean_text(
            item.get(
                "snippet"
            )
        )

        if (
            not title
            or not url
        ):
            continue

        parsed_url = (
            urlparse(
                url
            )
        )

        if parsed_url.scheme not in {
            "http",
            "https",
        }:
            continue

        canonical_url = (
            _canonical_url(
                url
            )
        )

        if canonical_url in (
            seen_urls
        ):
            continue

        seen_urls.add(
            canonical_url
        )

        domain = (
            _domain_from_url(
                canonical_url
            )
        )

        if not domain:
            continue

        (
            trust_tier,
            base_score,
        ) = _classify_candidate(
            domain=domain,
            title=title,
            snippet=snippet,
            url=canonical_url,
            trusted_domains=(
                trusted_domains
            ),
        )

        position_value = (
            item.get(
                "position"
            )
        )

        try:
            original_position = int(
                position_value
            )

        except (
            TypeError,
            ValueError,
        ):
            original_position = (
                index + 1
            )

        # Higher Google positions receive a small boost,
        # but source trust has much more influence.
        position_boost = max(
            0.0,
            12.0
            - float(
                original_position
            ),
        )

        ranking_score = (
            base_score
            + position_boost
        )

        candidate = (
            WebSearchCandidate(
                rank=1,
                original_position=(
                    original_position
                ),
                title=title,
                url=canonical_url,
                domain=domain,
                snippet=(
                    snippet
                    or None
                ),
                trust_tier=(
                    trust_tier
                ),
                ranking_score=(
                    ranking_score
                ),
            )
        )

        ranked_candidates.append(
            (
                ranking_score,
                original_position,
                candidate,
            )
        )

    ranked_candidates.sort(
        key=lambda value: (
            -value[0],
            value[1],
        )
    )

    selected = (
        ranked_candidates[
            :
            max_results
        ]
    )

    output: list[
        WebSearchCandidate
    ] = []

    for (
        index,
        (
            _score,
            _position,
            candidate,
        ),
    ) in enumerate(
        selected,
        start=1,
    ):
        output.append(
            candidate.model_copy(
                update={
                    "rank": index,
                }
            )
        )

    return output


# ---------------------------------------------------------
# Public service
# ---------------------------------------------------------


def search_web_with_serper(
    request: WebResearchInput,
) -> WebResearchOutput:
    max_results = min(
        request.max_results,
        settings.serper_max_results,
    )

    payload = _request_serper(
        query=request.query,
        num_results=max(
            max_results,
            10,
        ),
    )

    candidates = (
        _build_candidates(
            payload=payload,
            trusted_domains=(
                request.trusted_domains
            ),
            max_results=(
                max_results
            ),
        )
    )

    warnings: list[str] = []

    if not candidates:
        warnings.append(
            (
                "Serper completed successfully "
                "but returned no usable organic "
                "web results."
            )
        )

    return WebResearchOutput(
        ok=bool(
            candidates
        ),
        provider="serper",
        query=request.query,
        searched=True,
        candidate_count=len(
            candidates
        ),
        candidates=candidates,
        warnings=warnings,
    )