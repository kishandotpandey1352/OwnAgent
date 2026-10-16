from app.graphs.state import FinanceAgentState
from app.schemas.tools import AuditLogInput
from app.tools.registry import run_audit_log


def audit_agent_run_node(state: FinanceAgentState) -> FinanceAgentState:
    tool_results = state.get("tool_results", [])

    run_audit_log(
        user_id=state["user_id"],
        request_id=state["request_id"],
        tool_input=AuditLogInput(
            event_type="agent_run_completed",
            metadata={
                "question_length": len(state["question"]),
                "memory_used_count": state.get("memory_used_count", 0),
                "tool_call_count": len(tool_results),
                "tools": [
                    {
                        "tool_name": result.tool_name.value,
                        "status": result.status.value,
                    }
                    for result in tool_results
                ],
                "provider_id": state.get("provider_id"),
                "model": state.get("model"),
            },
        ),
    )

    return state