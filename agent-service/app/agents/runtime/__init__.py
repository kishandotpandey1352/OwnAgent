"""Multi-agent DAG runtime public API.

Heavy execution dependencies are loaded lazily so contract/model consumers do
not need provider/tool configuration merely to inspect persisted runtime data.
"""

from app.agents.runtime.models import DAGExecutionResult, DAGExecutionStatus

__all__ = [
    "DAGExecutor",
    "DAGExecutionResult",
    "DAGExecutionStatus",
    "SpecialistInputResolutionError",
    "execute_coordinator_plan",
    "resolve_specialist_input",
]


def __getattr__(name: str):
    if name in {"DAGExecutor", "execute_coordinator_plan"}:
        from app.agents.runtime.executor import DAGExecutor, execute_coordinator_plan

        return {"DAGExecutor": DAGExecutor, "execute_coordinator_plan": execute_coordinator_plan}[name]
    if name in {"SpecialistInputResolutionError", "resolve_specialist_input"}:
        from app.agents.runtime.inputs import SpecialistInputResolutionError, resolve_specialist_input

        return {
            "SpecialistInputResolutionError": SpecialistInputResolutionError,
            "resolve_specialist_input": resolve_specialist_input,
        }[name]
    raise AttributeError(name)
