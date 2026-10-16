from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone


class WebhookVerificationError(ValueError):
    pass


class WebhookReplayStore:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def claim(self, replay_key: str) -> bool:
        if replay_key in self._seen:
            return False
        self._seen.add(replay_key)
        return True


def sign_webhook(secret: str, *, timestamp: int, body: bytes) -> str:
    signed = f"{timestamp}.".encode("ascii") + body
    return hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()


def verify_webhook(
    *,
    secret: str,
    timestamp: int,
    body: bytes,
    signature: str,
    replay_store: WebhookReplayStore,
    replay_key: str,
    tolerance_seconds: int = 300,
    max_body_bytes: int = 1_000_000,
    now: datetime | None = None,
) -> None:
    if len(body) > max_body_bytes:
        raise WebhookVerificationError("Webhook body exceeds size limit.")

    current = now or datetime.now(timezone.utc)
    if abs(current.timestamp() - timestamp) > tolerance_seconds:
        raise WebhookVerificationError("Webhook timestamp is outside the replay window.")

    expected = sign_webhook(secret, timestamp=timestamp, body=body)
    if not hmac.compare_digest(expected, signature):
        raise WebhookVerificationError("Webhook signature is invalid.")

    if not replay_store.claim(replay_key):
        raise WebhookVerificationError("Webhook replay detected.")
