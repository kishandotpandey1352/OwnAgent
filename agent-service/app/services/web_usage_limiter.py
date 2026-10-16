from __future__ import annotations

import threading
import time

from collections import (
    defaultdict,
    deque,
)

from app.core.config import (
    settings,
)


# =========================================================
# Phase 3H-F-B
# Web usage limiter
# =========================================================


class WebUsageLimitError(
    RuntimeError
):
    pass


# ---------------------------------------------------------
# Process-local request history
#
# user_id ->
#     deque[timestamp]
# ---------------------------------------------------------

_lock = threading.Lock()

_requests: dict[
    str,
    deque[float],
] = defaultdict(
    deque
)


# =========================================================
# Helpers
# =========================================================


def _hourly_limit() -> int:
    return max(
        int(
            settings
            .web_max_searches_per_user_hour
        ),
        1,
    )


def _prune_history(
    *,
    history: deque[float],
    now: float,
) -> None:
    cutoff = (
        now
        - 3600.0
    )

    while (
        history
        and history[0]
        < cutoff
    ):
        history.popleft()


# =========================================================
# Public API
# =========================================================


def check_web_usage_limit(
    *,
    user_id: str,
) -> None:
    """
    Check and reserve one web-search allowance.

    This is intentionally process-local for the current MVP.

    For a horizontally scaled deployment, this should later
    be replaced by Redis or another shared atomic limiter.
    """

    clean_user_id = (
        str(
            user_id
        )
        .strip()
    )

    if not clean_user_id:
        raise WebUsageLimitError(
            "A user ID is required for web research."
        )

    limit = (
        _hourly_limit()
    )

    now = (
        time.time()
    )

    with _lock:
        history = (
            _requests[
                clean_user_id
            ]
        )

        _prune_history(
            history=history,
            now=now,
        )

        if (
            len(
                history
            )
            >= limit
        ):
            raise WebUsageLimitError(
                (
                    "Hourly web research limit "
                    "reached. Please try again later."
                )
            )

        # Reserve this search immediately so concurrent
        # requests cannot all pass the check together.
        history.append(
            now
        )


def web_usage_remaining(
    *,
    user_id: str,
) -> int:
    """
    Return remaining process-local searches available to the
    user during the current rolling one-hour window.
    """

    clean_user_id = (
        str(
            user_id
        )
        .strip()
    )

    if not clean_user_id:
        return 0

    limit = (
        _hourly_limit()
    )

    now = (
        time.time()
    )

    with _lock:
        history = (
            _requests[
                clean_user_id
            ]
        )

        _prune_history(
            history=history,
            now=now,
        )

        return max(
            limit
            - len(
                history
            ),
            0,
        )


def reset_web_usage_for_testing(
    *,
    user_id: str | None = None,
) -> None:
    """
    Test helper only.

    Allows deterministic unit tests without restarting the
    FastAPI process.
    """

    with _lock:
        if user_id is None:
            _requests.clear()
            return

        _requests.pop(
            str(
                user_id
            ),
            None,
        )