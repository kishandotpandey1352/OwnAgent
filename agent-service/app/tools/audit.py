from app.events.agent_events import write_agent_event
from app.schemas.tools import AuditLogInput, AuditLogOutput


def audit_log_tool(
    user_id: str,
    request_id: str,
    tool_input: AuditLogInput,
) -> AuditLogOutput:
    event = write_agent_event(
        user_id=user_id,
        request_id=request_id,
        event_type=tool_input.event_type,
        agent_name=tool_input.agent_name,
        metadata=tool_input.metadata,
    )

    return AuditLogOutput(
        ok=True,
        event_id=event["id"],
        event_type=tool_input.event_type,
    )