"""Coordinator public API with lazy loading of registry-dependent modules."""

__all__ = [
    "Coordinator",
    "CoordinatorPlanValidationError",
    "build_coordinator_plan",
    "validate_coordinator_plan",
]


def __getattr__(name: str):
    if name in {"Coordinator", "build_coordinator_plan"}:
        from app.agents.coordinator.coordinator import Coordinator, build_coordinator_plan

        return {"Coordinator": Coordinator, "build_coordinator_plan": build_coordinator_plan}[name]
    if name in {"CoordinatorPlanValidationError", "validate_coordinator_plan"}:
        from app.agents.coordinator.validator import CoordinatorPlanValidationError, validate_coordinator_plan

        return {
            "CoordinatorPlanValidationError": CoordinatorPlanValidationError,
            "validate_coordinator_plan": validate_coordinator_plan,
        }[name]
    raise AttributeError(name)
