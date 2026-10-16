from app.services.user_memory import list_active_user_memories


def memory_lookup_tool(user_id: str) -> dict:
    memories = list_active_user_memories(user_id)

    return {
        "memory_count": len(memories),
        "memories": [
            {
                "memory_type": memory.memory_type.value,
                "memory_key": memory.memory_key,
                "memory_value": memory.memory_value,
                "confidence": memory.confidence,
            }
            for memory in memories
        ],
    }