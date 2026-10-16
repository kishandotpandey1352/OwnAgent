from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, TypeVar

from app.agents.contracts import (
    AgentError,
    AgentName,
    AgentResult,
    AgentStatus,
    AgentTask,
    ExecutionContext,
)
from app.agents.registry import agent_can_use_tool, get_agent_definition
from app.schemas.tools import ToolName

T = TypeVar("T")


class SpecialistPolicyError(ValueError):
    """Raised when a specialist invocation violates its server-owned policy."""


class SpecialistAgent:
    agent_name: AgentName
    tool_name: ToolName
    version = "3I-B.v1"

    def _validate_common(
        self,
        *,
        task: AgentTask,
        context: ExecutionContext,
    ) -> None:
        if task.request_id != context.request_id:
            raise SpecialistPolicyError(
                "Task request_id does not match the execution context."
            )
        if task.agent_name != self.agent_name:
            raise SpecialistPolicyError(
                f"Task is assigned to {task.agent_name.value}, not {self.agent_name.value}."
            )

        definition = get_agent_definition(self.agent_name)
        if not agent_can_use_tool(self.agent_name, self.tool_name):
            raise SpecialistPolicyError(
                f"Agent {self.agent_name.value} is not permitted to use {self.tool_name.value}."
            )
        if self.tool_name not in definition.allowed_tools:
            raise SpecialistPolicyError("Agent registry/tool policy mismatch.")

    def _failure_result(
        self,
        *,
        task: AgentTask,
        started_at: datetime,
        started_clock: float,
        code: str,
        message: str,
        retryable: bool,
        metadata: dict[str, Any] | None = None,
    ) -> AgentResult:
        return AgentResult(
            task_id=task.task_id,
            request_id=task.request_id,
            agent_name=self.agent_name,
            status=AgentStatus.failed,
            evidence=[],
            warnings=[],
            error=AgentError(
                code=code,
                message=message,
                retryable=retryable,
                metadata=metadata or {},
            ),
            latency_ms=max(0, int((perf_counter() - started_clock) * 1000)),
            estimated_cost_usd=0.0,
            started_at=started_at,
            metadata={"agent_version": self.version},
        )

    def _execute_guarded(
        self,
        *,
        task: AgentTask,
        context: ExecutionContext,
        invoke: Callable[[], T],
        to_result: Callable[[T, datetime, float], AgentResult],
    ) -> AgentResult:
        started_at = datetime.now(timezone.utc)
        started_clock = perf_counter()

        try:
            self._validate_common(task=task, context=context)
            output = invoke()
            return to_result(output, started_at, started_clock)
        except SpecialistPolicyError as exc:
            return self._failure_result(
                task=task,
                started_at=started_at,
                started_clock=started_clock,
                code="AGENT_POLICY_DENIED",
                message=str(exc),
                retryable=False,
            )
        except ValueError:
            # Deterministic validation/tool-input failures will not improve on retry.
            return self._failure_result(
                task=task,
                started_at=started_at,
                started_clock=started_clock,
                code="AGENT_TOOL_REJECTED",
                message="The specialist tool rejected the requested input.",
                retryable=False,
            )
        except Exception:
            # Do not leak provider/database/internal exception text through the
            # inter-agent contract. Detailed diagnostics belong in server logs/audit.
            return self._failure_result(
                task=task,
                started_at=started_at,
                started_clock=started_clock,
                code="AGENT_TOOL_FAILURE",
                message="The specialist tool could not complete the requested task.",
                retryable=True,
            )
