import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pandas as pd

from app.schemas.data import DatasetMetadata


AGENT_SERVICE_ROOT = Path(__file__).resolve().parents[2]

DATASET_ROOT = (
    AGENT_SERVICE_ROOT
    / ".data"
    / "datasets"
)

MAX_CSV_BYTES = 10 * 1024 * 1024


class CsvStoreError(Exception):
    pass


class InvalidCsvError(CsvStoreError):
    pass


class CsvTooLargeError(CsvStoreError):
    pass


class DatasetNotFoundError(CsvStoreError):
    pass


class DatasetAccessError(CsvStoreError):
    pass


def _ensure_dataset_root() -> None:
    DATASET_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )


def _canonical_dataset_id(dataset_id: str) -> str:
    try:
        return str(UUID(dataset_id))
    except (ValueError, TypeError) as error:
        raise DatasetNotFoundError(
            f"Invalid dataset id: {dataset_id}"
        ) from error


def _dataset_directory(dataset_id: str) -> Path:
    canonical_id = _canonical_dataset_id(dataset_id)

    return DATASET_ROOT / canonical_id


def _csv_path(dataset_id: str) -> Path:
    return _dataset_directory(dataset_id) / "data.csv"


def _metadata_path(dataset_id: str) -> Path:
    return _dataset_directory(dataset_id) / "metadata.json"


def read_csv_dataframe(
    csv_path: Path,
) -> pd.DataFrame:
    try:
        dataframe = pd.read_csv(
            csv_path,
            dtype=str,
            keep_default_na=True,
            encoding="utf-8-sig",
        )

    except pd.errors.EmptyDataError as error:
        raise InvalidCsvError(
            "The CSV file is empty."
        ) from error

    except pd.errors.ParserError as error:
        raise InvalidCsvError(
            "The CSV file could not be parsed."
        ) from error

    except UnicodeDecodeError as error:
        raise InvalidCsvError(
            "The CSV must currently use UTF-8 encoding."
        ) from error

    except Exception as error:
        raise InvalidCsvError(
            f"Unable to read CSV: {error}"
        ) from error

    if len(dataframe.columns) == 0:
        raise InvalidCsvError(
            "The CSV does not contain any columns."
        )

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    return dataframe


def create_csv_dataset(
    *,
    user_id: str,
    file_name: str,
    content: bytes,
) -> DatasetMetadata:
    if not content:
        raise InvalidCsvError(
            "The uploaded CSV is empty."
        )

    if len(content) > MAX_CSV_BYTES:
        raise CsvTooLargeError(
            "CSV exceeds the current 10 MB upload limit."
        )

    _ensure_dataset_root()

    dataset_id = str(uuid4())

    dataset_directory = (
        DATASET_ROOT
        / dataset_id
    )

    dataset_directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    csv_path = dataset_directory / "data.csv"

    try:
        csv_path.write_bytes(content)

        dataframe = read_csv_dataframe(
            csv_path
        )

        metadata = DatasetMetadata(
            dataset_id=dataset_id,
            user_id=user_id,
            file_name=file_name,
            row_count=len(dataframe),
            column_count=len(dataframe.columns),
            size_bytes=len(content),
            created_at=datetime.now(timezone.utc),
        )

        metadata_path = (
            dataset_directory
            / "metadata.json"
        )

        metadata_path.write_text(
            json.dumps(
                metadata.model_dump(
                    mode="json"
                ),
                indent=2,
            ),
            encoding="utf-8",
        )

        return metadata

    except Exception:
        shutil.rmtree(
            dataset_directory,
            ignore_errors=True,
        )
        raise


def get_dataset_metadata(
    *,
    dataset_id: str,
    user_id: str,
) -> DatasetMetadata:
    metadata_path = _metadata_path(
        dataset_id
    )

    if not metadata_path.exists():
        raise DatasetNotFoundError(
            "Dataset not found."
        )

    try:
        raw_metadata = json.loads(
            metadata_path.read_text(
                encoding="utf-8"
            )
        )

        metadata = DatasetMetadata.model_validate(
            raw_metadata
        )

    except Exception as error:
        raise CsvStoreError(
            "Dataset metadata is corrupted."
        ) from error

    if metadata.user_id != user_id:
        raise DatasetAccessError(
            "You do not have access to this dataset."
        )

    return metadata


def load_csv_dataset(
    *,
    dataset_id: str,
    user_id: str,
) -> tuple[DatasetMetadata, pd.DataFrame]:
    metadata = get_dataset_metadata(
        dataset_id=dataset_id,
        user_id=user_id,
    )

    csv_path = _csv_path(
        dataset_id
    )

    if not csv_path.exists():
        raise DatasetNotFoundError(
            "Dataset CSV file was not found."
        )

    dataframe = read_csv_dataframe(
        csv_path
    )

    return metadata, dataframe


def delete_csv_dataset(
    *,
    dataset_id: str,
    user_id: str,
) -> bool:
    get_dataset_metadata(
        dataset_id=dataset_id,
        user_id=user_id,
    )

    dataset_directory = _dataset_directory(
        dataset_id
    )

    if not dataset_directory.exists():
        return False

    shutil.rmtree(
        dataset_directory
    )

    return True