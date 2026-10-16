from __future__ import annotations

import copy
import hashlib
import json
import threading
import time

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from app.core.config import (
    settings,
)


# =========================================================
# Phase 3H-F-C
# Process-local TTL web cache
# =========================================================


@dataclass
class _CacheEntry:
    value: Any

    expires_at: float


class _TTLCache:
    """
    Small thread-safe in-memory TTL/LRU cache.

    Intended for the current single-process / MVP backend.

    For multi-instance production deployment this should
    eventually move to Redis or another shared cache.
    """

    def __init__(
        self,
    ) -> None:
        self._lock = (
            threading.RLock()
        )

        self._items: OrderedDict[
            str,
            _CacheEntry,
        ] = OrderedDict()

    # -----------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------

    def _max_entries(
        self,
    ) -> int:
        return max(
            int(
                settings
                .web_cache_max_entries
            ),
            1,
        )

    def _prune_expired_locked(
        self,
        *,
        now: float,
    ) -> None:
        expired_keys = [
            key
            for (
                key,
                entry,
            )
            in self._items.items()
            if (
                entry.expires_at
                <= now
            )
        ]

        for key in expired_keys:
            self._items.pop(
                key,
                None,
            )

    def _enforce_size_locked(
        self,
    ) -> None:
        maximum = (
            self._max_entries()
        )

        while (
            len(
                self._items
            )
            > maximum
        ):
            self._items.popitem(
                last=False
            )

    # -----------------------------------------------------
    # Public operations
    # -----------------------------------------------------

    def get(
        self,
        key: str,
    ) -> Any | None:
        now = (
            time.monotonic()
        )

        with self._lock:
            self._prune_expired_locked(
                now=now
            )

            entry = (
                self._items.get(
                    key
                )
            )

            if entry is None:
                return None

            # LRU:
            # recently accessed value moves to the end.
            self._items.move_to_end(
                key
            )

            # Never hand callers the actual cached object.
            return copy.deepcopy(
                entry.value
            )

    def set(
        self,
        *,
        key: str,
        value: Any,
        ttl_seconds: int,
    ) -> None:
        ttl = max(
            int(
                ttl_seconds
            ),
            1,
        )

        expires_at = (
            time.monotonic()
            + ttl
        )

        with self._lock:
            self._prune_expired_locked(
                now=time.monotonic()
            )

            self._items[
                key
            ] = _CacheEntry(
                value=(
                    copy.deepcopy(
                        value
                    )
                ),
                expires_at=(
                    expires_at
                ),
            )

            self._items.move_to_end(
                key
            )

            self._enforce_size_locked()

    def clear(
        self,
    ) -> None:
        with self._lock:
            self._items.clear()

    def size(
        self,
    ) -> int:
        now = (
            time.monotonic()
        )

        with self._lock:
            self._prune_expired_locked(
                now=now
            )

            return len(
                self._items
            )


# =========================================================
# Cache instances
# =========================================================


_search_cache = (
    _TTLCache()
)

_fetch_cache = (
    _TTLCache()
)


# =========================================================
# Cache-key helpers
# =========================================================


def _stable_hash(
    value: dict[str, Any],
) -> str:
    serialized = json.dumps(
        value,
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


def _normalize_query(
    value: str,
) -> str:
    return " ".join(
        str(
            value
        )
        .strip()
        .split()
    ).casefold()


def _normalize_domains(
    values: list[str],
) -> list[str]:
    return sorted(
        {
            str(
                value
            )
            .strip()
            .lower()
            for value
            in values
            if str(
                value
            ).strip()
        }
    )


def build_web_search_cache_key(
    *,
    user_id: str,
    query: str,
    trusted_domains: list[str],
    max_results: int,
) -> str:
    """
    Per-user cache namespace.

    Keeping user_id in the key avoids sharing potentially
    sensitive query history between users, even though the
    underlying web information is public.
    """

    payload = {
        "version":
            "3h-f-c-search-v1",

        "user_id":
            str(
                user_id
            ).strip(),

        "query":
            _normalize_query(
                query
            ),

        "trusted_domains":
            _normalize_domains(
                trusted_domains
            ),

        "max_results":
            int(
                max_results
            ),

        "language":
            str(
                settings
                .serper_language
            ),
    }

    return (
        "web-search:"
        + _stable_hash(
            payload
        )
    )


def build_web_fetch_cache_key(
    *,
    user_id: str,
    query: str,
    candidate_urls: list[str],
) -> str:
    """
    Cache the result of the candidate-fetch stage.

    The key includes the discovered URL set so a changed
    Serper result automatically produces a different entry.
    """

    payload = {
        "version":
            "3h-f-c-fetch-v1",

        "user_id":
            str(
                user_id
            ).strip(),

        "query":
            _normalize_query(
                query
            ),

        "candidate_urls":
            sorted(
                {
                    str(
                        url
                    ).strip()
                    for url
                    in candidate_urls
                    if str(
                        url
                    ).strip()
                }
            ),
    }

    return (
        "web-fetch:"
        + _stable_hash(
            payload
        )
    )


# =========================================================
# Search cache
# =========================================================


def get_cached_web_search(
    *,
    key: str,
) -> Any | None:
    if not (
        settings
        .web_cache_enabled
    ):
        return None

    return (
        _search_cache.get(
            key
        )
    )


def set_cached_web_search(
    *,
    key: str,
    value: Any,
) -> None:
    if not (
        settings
        .web_cache_enabled
    ):
        return

    _search_cache.set(
        key=key,

        value=value,

        ttl_seconds=(
            settings
            .web_search_cache_ttl_seconds
        ),
    )


# =========================================================
# Fetch cache
# =========================================================


def get_cached_web_fetch(
    *,
    key: str,
) -> Any | None:
    if not (
        settings
        .web_cache_enabled
    ):
        return None

    return (
        _fetch_cache.get(
            key
        )
    )


def set_cached_web_fetch(
    *,
    key: str,
    value: Any,
) -> None:
    if not (
        settings
        .web_cache_enabled
    ):
        return

    _fetch_cache.set(
        key=key,

        value=value,

        ttl_seconds=(
            settings
            .web_fetch_cache_ttl_seconds
        ),
    )


# =========================================================
# Testing / diagnostics
# =========================================================


def reset_web_cache_for_testing() -> None:
    _search_cache.clear()

    _fetch_cache.clear()


def get_web_cache_sizes() -> dict[str, int]:
    return {
        "search":
            _search_cache.size(),

        "fetch":
            _fetch_cache.size(),
    }