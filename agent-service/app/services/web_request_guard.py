from __future__ import annotations

from dataclasses import (
    dataclass,
)

from app.core.config import (
    settings,
)

from app.schemas.web import (
    WebResearchInput,
)


# =========================================================
# Phase 3H-F-B
# Web request guard
# =========================================================


class WebRequestGuardError(
    ValueError
):
    pass


@dataclass(
    frozen=True
)
class GuardedWebRequest:
    query: str

    trusted_domains: list[str]

    max_results: int


# =========================================================
# Helpers
# =========================================================


def _clean_domain(
    value: str,
) -> str:
    domain = (
        str(
            value
        )
        .strip()
        .lower()
    )

    # trusted_domains should contain hostnames,
    # not arbitrary URLs.
    domain = (
        domain
        .removeprefix(
            "https://"
        )
        .removeprefix(
            "http://"
        )
        .strip("/")
    )

    # If somebody supplied:
    #
    #   example.com/path
    #
    # keep only:
    #
    #   example.com
    #
    if "/" in domain:
        domain = (
            domain
            .split(
                "/",
                1,
            )[0]
        )

    return domain


def _dedupe_domains(
    values: list[str],
) -> list[str]:
    result: list[str] = []

    seen: set[str] = set()

    for value in values:
        domain = (
            _clean_domain(
                value
            )
        )

        if not domain:
            continue

        if domain in seen:
            continue

        seen.add(
            domain
        )

        result.append(
            domain
        )

    return result


# =========================================================
# Public guard
# =========================================================


def guard_web_research_request(
    tool_input: WebResearchInput,
) -> GuardedWebRequest:
    query = (
        tool_input
        .query
        .strip()
    )

    if not query:
        raise WebRequestGuardError(
            "Web research query cannot be empty."
        )

    max_query_chars = max(
        int(
            settings
            .web_max_query_chars
        ),
        1,
    )

    if (
        len(
            query
        )
        > max_query_chars
    ):
        raise WebRequestGuardError(
            (
                "Web research query exceeds "
                f"{max_query_chars} characters."
            )
        )

    trusted_domains = (
        _dedupe_domains(
            list(
                tool_input
                .trusted_domains
                or []
            )
        )
    )

    max_domains = max(
        int(
            settings
            .web_max_trusted_domains
        ),
        0,
    )

    if (
        len(
            trusted_domains
        )
        > max_domains
    ):
        raise WebRequestGuardError(
            (
                "Too many trusted web domains "
                f"were supplied. Maximum: "
                f"{max_domains}."
            )
        )

    requested_results = max(
        int(
            tool_input
            .max_results
            or 1
        ),
        1,
    )

    product_max_results = max(
        int(
            settings
            .web_max_results_per_search
        ),
        1,
    )

    provider_max_results = max(
        int(
            settings
            .serper_max_results
        ),
        1,
    )

    effective_max_results = min(
        requested_results,
        product_max_results,
        provider_max_results,
    )

    return GuardedWebRequest(
        query=query,

        trusted_domains=(
            trusted_domains
        ),

        max_results=(
            effective_max_results
        ),
    )