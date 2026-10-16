from fastapi import APIRouter, Header, HTTPException

from app.schemas.memory import (
    BasicOkResponse,
    MemoryActionRequest,
    MemoryListResponse,
    MemoryResponse,
    ProposeMemoryRequest,
)
from app.services.user_memory import (
    confirm_user_memory,
    delete_user_memory,
    list_user_memories,
    propose_user_memory,
)

from app.schemas.memory import DetectMemoryRequest, DetectMemoryResponse
from app.services.memory_detector import detect_memory_suggestion


router = APIRouter(prefix="/memory", tags=["memory"])


def get_user_id(x_user_id: str | None) -> str:
    return x_user_id or "local-demo-user"


@router.get("/list", response_model=MemoryListResponse)
def list_memory(x_user_id: str | None = Header(default=None)):
    user_id = get_user_id(x_user_id)
    memories = list_user_memories(user_id)

    return MemoryListResponse(ok=True, memories=memories)


@router.post("/propose", response_model=MemoryResponse)
def propose_memory(
    request: ProposeMemoryRequest,
    x_user_id: str | None = Header(default=None),
):
    try:
        user_id = get_user_id(x_user_id)
        memory = propose_user_memory(user_id, request)
        return MemoryResponse(ok=True, memory=memory)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/confirm", response_model=MemoryResponse)
def confirm_memory(
    request: MemoryActionRequest,
    x_user_id: str | None = Header(default=None),
):
    try:
        user_id = get_user_id(x_user_id)
        memory = confirm_user_memory(user_id, request.memory_id)
        return MemoryResponse(ok=True, memory=memory)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/delete", response_model=BasicOkResponse)
def delete_memory(
    request: MemoryActionRequest,
    x_user_id: str | None = Header(default=None),
):
    try:
        user_id = get_user_id(x_user_id)
        delete_user_memory(user_id, request.memory_id)
        return BasicOkResponse(ok=True)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

@router.post("/detect", response_model=DetectMemoryResponse)
def detect_memory(request: DetectMemoryRequest):
    suggestion = detect_memory_suggestion(request.text)

    return DetectMemoryResponse(
        ok=True,
        suggestion=suggestion,
    )