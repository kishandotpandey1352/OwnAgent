import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.memory import MemoryType, ProposeMemoryRequest, UserMemory


MEMORY_DIR = Path(".data/user-memory")
MEMORY_FILE = MEMORY_DIR / "memories.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_memory_file() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if not MEMORY_FILE.exists():
        MEMORY_FILE.write_text("[]", encoding="utf-8")


def _read_memories() -> list[UserMemory]:
    _ensure_memory_file()

    raw = MEMORY_FILE.read_text(encoding="utf-8")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = []

    return [UserMemory.model_validate(item) for item in data]


def _write_memories(memories: list[UserMemory]) -> None:
    _ensure_memory_file()

    MEMORY_FILE.write_text(
        json.dumps(
            [memory.model_dump(mode="json") for memory in memories],
            indent=2,
        ),
        encoding="utf-8",
    )


def _normalize_key(value: str) -> str:
    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9_-]+", "_", normalized)
    normalized = normalized.strip("_")

    if not normalized:
        raise ValueError("memory_key is required.")

    return normalized[:80]


def _normalize_value(value: str) -> str:
    normalized = " ".join(value.strip().split())

    if not normalized:
        raise ValueError("memory_value is required.")

    if len(normalized) > 500:
        raise ValueError("memory_value must be 500 characters or less.")

    return normalized


def list_user_memories(user_id: str) -> list[UserMemory]:
    memories = _read_memories()

    return sorted(
        [
            memory
            for memory in memories
            if memory.user_id == user_id and memory.deleted_at is None
        ],
        key=lambda memory: memory.updated_at,
        reverse=True,
    )


def list_active_user_memories(user_id: str) -> list[UserMemory]:
    return [
        memory
        for memory in list_user_memories(user_id)
        if memory.status == "active" and memory.is_active
    ]


def propose_user_memory(user_id: str, request: ProposeMemoryRequest) -> UserMemory:
    from uuid import uuid4

    timestamp = _now()

    memory = UserMemory(
        id=str(uuid4()),
        user_id=user_id,
        memory_type=request.memory_type,
        memory_key=_normalize_key(request.memory_key),
        memory_value=_normalize_value(request.memory_value),
        confidence=request.confidence,
        source=request.source,
        status="proposed",
        is_active=False,
        metadata=request.metadata,
        created_at=timestamp,
        updated_at=timestamp,
    )

    memories = _read_memories()
    memories.insert(0, memory)
    _write_memories(memories)

    return memory


def confirm_user_memory(user_id: str, memory_id: str) -> UserMemory:
    memories = _read_memories()
    timestamp = _now()

    target = next(
        (
            memory
            for memory in memories
            if memory.user_id == user_id
            and memory.id == memory_id
            and memory.deleted_at is None
        ),
        None,
    )

    if target is None:
        raise ValueError("Memory not found.")

    for memory in memories:
        same_user = memory.user_id == user_id
        same_type = memory.memory_type == target.memory_type
        same_key = memory.memory_key == target.memory_key
        different_record = memory.id != target.id

        if same_user and same_type and same_key and different_record:
            memory.is_active = False
            memory.updated_at = timestamp

    target.status = "active"
    target.is_active = True
    target.source = "user-confirmed"
    target.confirmed_at = timestamp
    target.updated_at = timestamp

    _write_memories(memories)

    return target


def delete_user_memory(user_id: str, memory_id: str) -> None:
    memories = _read_memories()
    timestamp = _now()

    target = next(
        (
            memory
            for memory in memories
            if memory.user_id == user_id
            and memory.id == memory_id
            and memory.deleted_at is None
        ),
        None,
    )

    if target is None:
        raise ValueError("Memory not found.")

    target.status = "deleted"
    target.is_active = False
    target.deleted_at = timestamp
    target.updated_at = timestamp

    _write_memories(memories)


def format_memories_for_prompt(memories: list[UserMemory]) -> str:
    active_memories = [
        memory
        for memory in memories
        if memory.status == "active" and memory.is_active
    ]

    if not active_memories:
        return ""

    return "\n".join(
        [
            f"- {memory.memory_type.value}/{memory.memory_key}: {memory.memory_value}"
            for memory in active_memories
        ]
    )


def build_memory_context(user_id: str) -> str:
    memories = list_active_user_memories(user_id)
    formatted = format_memories_for_prompt(memories)

    if not formatted:
        return ""

    return (
        "Confirmed user preferences. Use these for style and workflow only, "
        "not as factual financial evidence:\n"
        f"{formatted}"
    )