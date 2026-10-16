from app.core.config import (
    settings,
)

from app.schemas.web import (
    WebResearchInput,
)

from app.services.web_request_guard import (
    WebRequestGuardError,
    guard_web_research_request,
)

from app.services.web_usage_limiter import (
    WebUsageLimitError,
    check_web_usage_limit,
    reset_web_usage_for_testing,
    web_usage_remaining,
)


TEST_USER = (
    "3h-f-b-test-user"
)

def test_request_guard() -> None:
    print(
        "\n=== REQUEST GUARD ==="
    )

    request = (
        WebResearchInput(
            query=(
                "Ambac commission income 2025"
            ),

            gap_reason=(
                "Uploaded evidence incomplete."
            ),

            trusted_domains=[
                "octavegroup.com",
                "https://octavegroup.com/",
                "SEC.GOV",
            ],

            # WebResearchInput itself allows a maximum
            # of 20. The 3H-F-B product guard should
            # reduce this further to the configured
            # product/provider ceiling.
            max_results=20,

            extract_structured_facts=True,
        )
    )

    guarded = (
        guard_web_research_request(
            request
        )
    )

    print(
        "Original max results:",
        request.max_results,
    )

    print(
        "Guarded query:",
        guarded.query,
    )

    print(
        "Guarded domains:",
        guarded.trusted_domains,
    )

    print(
        "Guarded max results:",
        guarded.max_results,
    )

    assert guarded.query == (
        "Ambac commission income 2025"
    )

    # Duplicate/case/URL forms should normalize.
    assert guarded.trusted_domains == [
        "octavegroup.com",
        "sec.gov",
    ]

    # The request asked for 20, but F-B must not allow
    # more than either the product maximum or Serper
    # provider maximum.
    assert (
        guarded.max_results
        <= settings
        .web_max_results_per_search
    )

    assert (
        guarded.max_results
        <= settings
        .serper_max_results
    )

    assert (
        guarded.max_results
        <= request.max_results
    )

    expected_max = min(
        request.max_results,
        settings.web_max_results_per_search,
        settings.serper_max_results,
    )

    assert (
        guarded.max_results
        == expected_max
    )

    print(
        "PASS: request guard works"
    )

def test_query_limit() -> None:
    print(
        "\n=== QUERY LIMIT ==="
    )

    too_long = (
        "x"
        * (
            settings
            .web_max_query_chars
            + 1
        )
    )

    request = (
        WebResearchInput(
            query=too_long,

            gap_reason="test",

            trusted_domains=[],

            max_results=1,

            extract_structured_facts=False,
        )
    )

    try:
        guard_web_research_request(
            request
        )

    except WebRequestGuardError:
        print(
            "PASS: oversized query blocked"
        )
        return

    raise AssertionError(
        "Oversized query was not blocked."
    )


def test_domain_limit() -> None:
    print(
        "\n=== DOMAIN LIMIT ==="
    )

    domains = [
        f"example{i}.com"
        for i
        in range(
            settings
            .web_max_trusted_domains
            + 1
        )
    ]

    request = (
        WebResearchInput(
            query="test",

            gap_reason="test",

            trusted_domains=domains,

            max_results=1,

            extract_structured_facts=False,
        )
    )

    try:
        guard_web_research_request(
            request
        )

    except WebRequestGuardError:
        print(
            "PASS: excessive domains blocked"
        )
        return

    raise AssertionError(
        "Excessive domains were not blocked."
    )


def test_hourly_rate_limit() -> None:
    print(
        "\n=== HOURLY RATE LIMIT ==="
    )

    reset_web_usage_for_testing(
        user_id=TEST_USER
    )

    limit = (
        settings
        .web_max_searches_per_user_hour
    )

    print(
        "Configured hourly limit:",
        limit,
    )

    for index in range(
        limit
    ):
        check_web_usage_limit(
            user_id=TEST_USER
        )

        remaining = (
            web_usage_remaining(
                user_id=TEST_USER
            )
        )

        print(
            (
                f"Request "
                f"{index + 1}/{limit} "
                f"remaining={remaining}"
            )
        )

    try:
        check_web_usage_limit(
            user_id=TEST_USER
        )

    except WebUsageLimitError:
        print(
            "PASS: hourly limit enforced"
        )

        reset_web_usage_for_testing(
            user_id=TEST_USER
        )

        return

    raise AssertionError(
        "Hourly rate limit was not enforced."
    )


def main() -> None:
    test_request_guard()

    test_query_limit()

    test_domain_limit()

    test_hourly_rate_limit()

    print(
        "\nPASS: 3H-F-B cost controls work."
    )


if __name__ == "__main__":
    main()