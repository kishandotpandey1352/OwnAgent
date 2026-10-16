from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class DataClassification(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"
    secret = "secret"


class DataCategory(str, Enum):
    public_web_url = "public_web_url"
    model_version = "model_version"
    user_prompt = "user_prompt"
    uploaded_financial_file = "uploaded_financial_file"
    provider_secret = "provider_secret"
    operational_log = "operational_log"
    detailed_trace = "detailed_trace"
    compliance_record = "compliance_record"
    web_cache = "web_cache"
    user_document = "user_document"


DEFAULT_CLASSIFICATION: dict[DataCategory, DataClassification] = {
    DataCategory.public_web_url: DataClassification.public,
    DataCategory.model_version: DataClassification.internal,
    DataCategory.user_prompt: DataClassification.confidential,
    DataCategory.uploaded_financial_file: DataClassification.confidential,
    DataCategory.provider_secret: DataClassification.secret,
    DataCategory.operational_log: DataClassification.internal,
    DataCategory.detailed_trace: DataClassification.internal,
    DataCategory.compliance_record: DataClassification.restricted,
    DataCategory.web_cache: DataClassification.internal,
    DataCategory.user_document: DataClassification.confidential,
}


class RetentionRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: DataCategory
    retention_days: int | None = Field(default=None, ge=1)
    user_controlled: bool = False
    legal_policy_controlled: bool = False

    def expires_at(self, created_at: datetime) -> datetime | None:
        if self.retention_days is None:
            return None
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("created_at must be timezone-aware")
        return created_at + timedelta(days=self.retention_days)


DEFAULT_RETENTION: dict[DataCategory, RetentionRule] = {
    DataCategory.operational_log: RetentionRule(category=DataCategory.operational_log, retention_days=30),
    DataCategory.detailed_trace: RetentionRule(category=DataCategory.detailed_trace, retention_days=90),
    DataCategory.compliance_record: RetentionRule(category=DataCategory.compliance_record, legal_policy_controlled=True),
    DataCategory.web_cache: RetentionRule(category=DataCategory.web_cache, retention_days=1),
    DataCategory.user_document: RetentionRule(category=DataCategory.user_document, user_controlled=True),
    DataCategory.user_prompt: RetentionRule(category=DataCategory.user_prompt, retention_days=90),
    DataCategory.public_web_url: RetentionRule(category=DataCategory.public_web_url, retention_days=90),
    DataCategory.model_version: RetentionRule(category=DataCategory.model_version, legal_policy_controlled=True),
    DataCategory.uploaded_financial_file: RetentionRule(category=DataCategory.uploaded_financial_file, user_controlled=True),
    DataCategory.provider_secret: RetentionRule(category=DataCategory.provider_secret, legal_policy_controlled=True),
}


def classification_for(category: DataCategory) -> DataClassification:
    return DEFAULT_CLASSIFICATION[category]


def is_expired(category: DataCategory, *, created_at: datetime, now: datetime | None = None) -> bool:
    rule = DEFAULT_RETENTION[category]
    expiry = rule.expires_at(created_at)
    if expiry is None:
        return False
    current = now or datetime.now(timezone.utc)
    return current >= expiry
