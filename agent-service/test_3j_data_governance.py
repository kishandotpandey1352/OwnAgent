from datetime import datetime, timedelta, timezone

from app.governance import DataCategory, DataClassification, classification_for, is_expired

assert classification_for(DataCategory.provider_secret) == DataClassification.secret
assert classification_for(DataCategory.uploaded_financial_file) == DataClassification.confidential
created = datetime.now(timezone.utc) - timedelta(days=31)
assert is_expired(DataCategory.operational_log, created_at=created) is True
assert is_expired(DataCategory.compliance_record, created_at=created) is False
print("PASS: 3J data classification and retention policy foundation validated.")
