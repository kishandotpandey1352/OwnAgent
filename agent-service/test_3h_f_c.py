import time

from app.services.web_cache import (
    build_web_fetch_cache_key,
    build_web_search_cache_key,
    get_cached_web_fetch,
    get_cached_web_search,
    get_web_cache_sizes,
    reset_web_cache_for_testing,
    set_cached_web_fetch,
    set_cached_web_search,
)


def main() -> None:
    print(
        "\n=== 3H-F-C CACHE TEST ==="
    )

    reset_web_cache_for_testing()

    # =====================================================
    # Search cache key stability
    # =====================================================

    key_1 = (
        build_web_search_cache_key(
            user_id="test-user",

            query=(
                " Ambac   commission income 2025 "
            ),

            trusted_domains=[
                "sec.gov",
                "octavegroup.com",
            ],

            max_results=8,
        )
    )

    key_2 = (
        build_web_search_cache_key(
            user_id="test-user",

            query=(
                "ambac commission income 2025"
            ),

            trusted_domains=[
                "octavegroup.com",
                "sec.gov",
            ],

            max_results=8,
        )
    )

    assert (
        key_1
        == key_2
    )

    print(
        "PASS: equivalent search requests "
        "produce the same cache key"
    )

    # =====================================================
    # Different users must not share cache entries
    # =====================================================

    other_user_key = (
        build_web_search_cache_key(
            user_id="different-user",

            query=(
                "ambac commission income 2025"
            ),

            trusted_domains=[
                "octavegroup.com",
                "sec.gov",
            ],

            max_results=8,
        )
    )

    assert (
        key_1
        != other_user_key
    )

    print(
        "PASS: web cache is user-scoped"
    )

    # =====================================================
    # Search cache miss / hit
    # =====================================================

    assert (
        get_cached_web_search(
            key=key_1
        )
        is None
    )

    print(
        "PASS: initial search cache miss"
    )

    fake_search_result = {
        "provider":
            "serper",

        "candidate_count":
            3,
    }

    set_cached_web_search(
        key=key_1,
        value=(
            fake_search_result
        ),
    )

    cached_search = (
        get_cached_web_search(
            key=key_1
        )
    )

    assert (
        cached_search
        == fake_search_result
    )

    print(
        "PASS: search cache hit"
    )

    # =====================================================
    # Deep-copy protection
    # =====================================================

    cached_search[
        "candidate_count"
    ] = 999

    cached_again = (
        get_cached_web_search(
            key=key_1
        )
    )

    assert (
        cached_again[
            "candidate_count"
        ]
        == 3
    )

    print(
        "PASS: cached values are protected "
        "from caller mutation"
    )

    # =====================================================
    # Fetch cache
    # =====================================================

    fetch_key = (
        build_web_fetch_cache_key(
            user_id="test-user",

            query=(
                "Ambac commission income 2025"
            ),

            candidate_urls=[
                "https://example.com/b",
                "https://example.com/a",
            ],
        )
    )

    assert (
        get_cached_web_fetch(
            key=fetch_key
        )
        is None
    )

    print(
        "PASS: initial fetch cache miss"
    )

    fake_fetch_result = (
        [
            {
                "url":
                    "https://example.com/a",
            }
        ],
        [],
    )

    set_cached_web_fetch(
        key=fetch_key,

        value=(
            fake_fetch_result
        ),
    )

    cached_fetch = (
        get_cached_web_fetch(
            key=fetch_key
        )
    )

    assert (
        cached_fetch
        == fake_fetch_result
    )

    print(
        "PASS: fetch cache hit"
    )

    # =====================================================
    # Cache diagnostics
    # =====================================================

    sizes = (
        get_web_cache_sizes()
    )

    print(
        "Cache sizes:",
        sizes,
    )

    assert (
        sizes[
            "search"
        ]
        == 1
    )

    assert (
        sizes[
            "fetch"
        ]
        == 1
    )

    reset_web_cache_for_testing()

    print(
        "\nPASS: 3H-F-C cache service works."
    )


if __name__ == "__main__":
    main()