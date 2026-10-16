from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.automation.contracts import AutomationEvent
from app.automation.idempotency import IdempotencyStatus, IdempotencyStore
from app.automation.workflow import WorkflowRecord, WorkflowState, WorkflowStateMachine


@dataclass(frozen=True)
class AutomationRunResult:
    workflow: WorkflowRecord
    result: Any
    duplicate: bool = False


WorkflowRunner = Callable[[AutomationEvent], Any]
AsyncWorkflowRunner = Callable[[AutomationEvent], Awaitable[Any]]
AuditCallback = Callable[[str, dict[str, Any]], None]


class AutomationEngine:
    """Reference event-to-workflow engine.

    The injected runner is where production integration invokes the governed
    3I pipeline. This class owns idempotency and explicit workflow state; it
    never runs important work inside an untracked web request.
    """

    def __init__(
        self,
        *,
        runner: WorkflowRunner,
        idempotency: IdempotencyStore | None = None,
        audit: AuditCallback | None = None,
    ) -> None:
        self.runner = runner
        self.idempotency = idempotency or IdempotencyStore()
        self.audit = audit
        self.state_machine = WorkflowStateMachine()
        self.workflows: dict[str, WorkflowRecord] = {}

    def process(self, event: AutomationEvent) -> AutomationRunResult:
        created, record = self.idempotency.begin(event.idempotency_key)
        if not created:
            workflow = next(
                (
                    item
                    for item in self.workflows.values()
                    if item.event_id == event.event_id
                ),
                WorkflowRecord(
                    workflow_id=f"duplicate-{event.event_id}",
                    event_id=event.event_id,
                    tenant_id=event.tenant_id,
                    state=(
                        WorkflowState.completed
                        if record.status == IdempotencyStatus.completed
                        else WorkflowState.failed
                        if record.status == IdempotencyStatus.failed
                        else WorkflowState.running
                    ),
                ),
            )
            return AutomationRunResult(workflow=workflow, result=record.result, duplicate=True)

        workflow = WorkflowRecord(
            workflow_id=f"wf-{uuid4()}",
            event_id=event.event_id,
            tenant_id=event.tenant_id,
        )
        workflow = self.state_machine.transition(workflow, WorkflowState.running)
        self.workflows[workflow.workflow_id] = workflow
        self._audit("automation.workflow.started", {"workflow_id": workflow.workflow_id, "event_id": event.event_id, "tenant_id": event.tenant_id, "user_id": event.user_id})

        try:
            result = self.runner(event)
            workflow = self.state_machine.transition(workflow, WorkflowState.completed)
            self.workflows[workflow.workflow_id] = workflow
            self.idempotency.complete(event.idempotency_key, result)
            self._audit("automation.workflow.completed", {"workflow_id": workflow.workflow_id, "event_id": event.event_id, "tenant_id": event.tenant_id, "user_id": event.user_id})
            return AutomationRunResult(workflow=workflow, result=result)
        except Exception as exc:
            workflow = workflow.model_copy(
                update={"last_error": type(exc).__name__, "attempts": workflow.attempts + 1}
            )
            workflow = self.state_machine.transition(workflow, WorkflowState.failed)
            self.workflows[workflow.workflow_id] = workflow
            self.idempotency.fail(event.idempotency_key, str(exc))
            self._audit(
                "automation.workflow.failed",
                {"workflow_id": workflow.workflow_id, "event_id": event.event_id, "tenant_id": event.tenant_id, "user_id": event.user_id, "error": type(exc).__name__},
            )
            raise


    async def process_async(
        self,
        event: AutomationEvent,
        *,
        runner: AsyncWorkflowRunner,
        retry_failed: bool = True,
    ) -> AutomationRunResult:
        created, record = self.idempotency.begin(
            event.idempotency_key,
            retry_failed=retry_failed,
        )
        if not created:
            workflow = next(
                (item for item in self.workflows.values() if item.event_id == event.event_id),
                WorkflowRecord(
                    workflow_id=f"duplicate-{event.event_id}",
                    event_id=event.event_id,
                    tenant_id=event.tenant_id,
                    state=(
                        WorkflowState.completed
                        if record.status == IdempotencyStatus.completed
                        else WorkflowState.failed
                        if record.status == IdempotencyStatus.failed
                        else WorkflowState.running
                    ),
                ),
            )
            return AutomationRunResult(workflow=workflow, result=record.result, duplicate=True)

        workflow = WorkflowRecord(
            workflow_id=f"wf-{uuid4()}",
            event_id=event.event_id,
            tenant_id=event.tenant_id,
        )
        workflow = self.state_machine.transition(workflow, WorkflowState.running)
        self.workflows[workflow.workflow_id] = workflow
        self._audit("automation.workflow.started", {"workflow_id": workflow.workflow_id, "event_id": event.event_id, "tenant_id": event.tenant_id, "user_id": event.user_id})
        try:
            result = await runner(event)
            workflow = self.state_machine.transition(workflow, WorkflowState.completed)
            self.workflows[workflow.workflow_id] = workflow
            self.idempotency.complete(event.idempotency_key, result)
            self._audit("automation.workflow.completed", {"workflow_id": workflow.workflow_id, "event_id": event.event_id, "tenant_id": event.tenant_id, "user_id": event.user_id})
            return AutomationRunResult(workflow=workflow, result=result)
        except Exception as exc:
            workflow = workflow.model_copy(
                update={"last_error": type(exc).__name__, "attempts": workflow.attempts + 1}
            )
            workflow = self.state_machine.transition(workflow, WorkflowState.failed)
            self.workflows[workflow.workflow_id] = workflow
            self.idempotency.fail(event.idempotency_key, str(exc))
            self._audit(
                "automation.workflow.failed",
                {"workflow_id": workflow.workflow_id, "event_id": event.event_id, "tenant_id": event.tenant_id, "user_id": event.user_id, "error": type(exc).__name__},
            )
            raise

    def _audit(self, event_type: str, metadata: dict[str, Any]) -> None:
        if self.audit is not None:
            self.audit(event_type, metadata)
