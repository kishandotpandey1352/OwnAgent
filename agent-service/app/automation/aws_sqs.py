from __future__ import annotations

import hashlib
import json
from typing import Any

from app.automation.contracts import AutomationEvent
from app.automation.ordering import ordering_policy


class SQSQueueAdapter:
    """Thin production adapter for AWS SQS.

    boto3 is imported lazily so local/test installations do not need the AWS
    SDK. Queue IAM policy, KMS encryption, DLQ/redrive and visibility timeout
    are deployment concerns and must be configured in infrastructure-as-code.
    """

    def __init__(self, *, queue_url: str, client: Any | None = None) -> None:
        if client is None:
            try:
                import boto3  # type: ignore
            except ImportError as exc:
                raise RuntimeError("boto3 is required for SQSQueueAdapter") from exc
            client = boto3.client("sqs")
        self.client = client
        self.queue_url = queue_url

    @staticmethod
    def _dedup_id(value: str) -> str:
        if len(value.encode("utf-8")) <= 128:
            return value
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def send(self, event: AutomationEvent) -> str:
        kwargs: dict[str, Any] = {
            "QueueUrl": self.queue_url,
            "MessageBody": event.model_dump_json(),
        }
        if self.queue_url.endswith(".fifo"):
            ordering = ordering_policy(event)
            kwargs["MessageGroupId"] = ordering.ordering_key or event.tenant_id
            kwargs["MessageDeduplicationId"] = self._dedup_id(event.idempotency_key)
        response = self.client.send_message(**kwargs)
        return str(response["MessageId"])

    def receive(self, *, wait_time_seconds: int = 10) -> tuple[AutomationEvent, str] | None:
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=wait_time_seconds,
        )
        messages = response.get("Messages") or []
        if not messages:
            return None
        message = messages[0]
        event = AutomationEvent.model_validate(json.loads(message["Body"]))
        return event, message["ReceiptHandle"]

    def ack(self, receipt_handle: str) -> None:
        self.client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receipt_handle,
        )
