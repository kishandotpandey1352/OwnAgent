from app.graphs.state import FinanceAgentState
from app.services.user_memory import build_memory_context, list_active_user_memories


def load_memory_node(state: FinanceAgentState) -> FinanceAgentState:
    user_id = state["user_id"]

    active_memories = list_active_user_memories(user_id)
    memory_context = build_memory_context(user_id)

    return {
        **state,
        "memory_context": memory_context,
        "memory_used_count": len(active_memories),
    }