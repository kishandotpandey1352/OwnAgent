import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


EVENT_DIR = Path(".data/agent-events")
EVENT_FILE = EVENT_DIR / "events.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_agent_event(
    user_id: str,
    request_id: str,
    event_type: str,
    agent_name: str = "finance_memory_agent",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    EVENT_DIR.mkdir(parents=True, exist_ok=True)

    event = {
        "id": str(uuid4()),
        "user_id": user_id,
        "request_id": request_id,
        "event_type": event_type,
        "agent_name": agent_name,
        "metadata": metadata or {},
        "created_at": _now_iso(),
    }

    with EVENT_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event) + "\n")

    return event