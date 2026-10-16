from fastapi import (
    APIRouter,
    File,
    Header,
    HTTPException,
    UploadFile,
)

from app.schemas.data import (
    DatasetDeleteResponse,
    DatasetProfileResponse,
    DatasetUploadResponse,
)
from app.services.csv_store import (
    CsvStoreError,
    CsvTooLargeError,
    DatasetAccessError,
    DatasetNotFoundError,
    InvalidCsvError,
    create_csv_dataset,
    delete_csv_dataset,
)
from app.tools.csv_profile import (
    profile_csv_dataset,
)

from app.schemas.chart import (
    ChartRequest,
    ChartSpecResponse,
)

from app.tools.chart_planner import (
    ChartBuildError,
    build_chart_spec,
)


router = APIRouter(
    prefix="/data",
    tags=["data"],
)


def get_user_id(
    header_user_id: str | None,
) -> str:
    return (
        header_user_id
        or "local-demo-user"
    )


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
)
async def upload_csv(
    file: UploadFile = File(...),
    x_user_id: str | None = Header(
        default=None
    ),
):
    user_id = get_user_id(
        x_user_id
    )

    file_name = (
        file.filename
        or "dataset.csv"
    )

    if not file_name.lower().endswith(
        ".csv"
    ):
        raise HTTPException(
            status_code=415,
            detail=(
                "Only CSV files are "
                "supported in Phase 3E."
            ),
        )

    try:
        content = await file.read()

        metadata = create_csv_dataset(
            user_id=user_id,
            file_name=file_name,
            content=content,
        )

        return DatasetUploadResponse(
            dataset_id=metadata.dataset_id,
            file_name=metadata.file_name,
            row_count=metadata.row_count,
            column_count=metadata.column_count,
            size_bytes=metadata.size_bytes,
            created_at=metadata.created_at,
        )

    except CsvTooLargeError as error:
        raise HTTPException(
            status_code=413,
            detail=str(error),
        ) from error

    except InvalidCsvError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except CsvStoreError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    finally:
        await file.close()


@router.get(
    "/profile/{dataset_id}",
    response_model=DatasetProfileResponse,
)
def profile_csv(
    dataset_id: str,
    x_user_id: str | None = Header(
        default=None
    ),
):
    user_id = get_user_id(
        x_user_id
    )

    try:
        return profile_csv_dataset(
            dataset_id=dataset_id,
            user_id=user_id,
        )

    except DatasetNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except DatasetAccessError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error

    except InvalidCsvError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except CsvStoreError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

@router.post(
    "/chart",
    response_model=ChartSpecResponse,
)
def create_chart(
    request: ChartRequest,
    x_user_id: str | None = Header(
        default=None
    ),
):
    user_id = get_user_id(
        x_user_id
    )

    try:
        return build_chart_spec(
            user_id=user_id,
            request=request,
        )

    except DatasetNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except DatasetAccessError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error

    except ChartBuildError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except InvalidCsvError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error

    except CsvStoreError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


@router.delete(
    "/{dataset_id}",
    response_model=DatasetDeleteResponse,
)
def delete_csv(
    dataset_id: str,
    x_user_id: str | None = Header(
        default=None
    ),
):
    user_id = get_user_id(
        x_user_id
    )

    try:
        deleted = delete_csv_dataset(
            dataset_id=dataset_id,
            user_id=user_id,
        )

        return DatasetDeleteResponse(
            dataset_id=dataset_id,
            deleted=deleted,
        )

    except DatasetNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except DatasetAccessError as error:
        raise HTTPException(
            status_code=403,
            detail=str(error),
        ) from error

    except CsvStoreError as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error