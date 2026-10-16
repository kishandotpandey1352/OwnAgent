from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AutomationPermission(str, Enum):
    retrieve_public_filings = "retrieve_public_filings"
    run_finance_agents = "run_finance_agents"
    read_tenant_documents = "read_tenant_documents"
    store_report = "store_report"
    create_chart = "create_chart"
    send_external_message = "send_external_message"
    modify_external_system = "modify_external_system"
    execute_financial_transaction = "execute_financial_transaction"


class WorkflowIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    workflow_name: str
    tenant_id: str
    allowed_permissions: frozenset[AutomationPermission] = Field(default_factory=frozenset)

    def authorize(self, permission: AutomationPermission, *, tenant_id: str) -> None:
        if tenant_id != self.tenant_id:
            raise PermissionError("Automation workflow attempted cross-tenant access.")
        if permission not in self.allowed_permissions:
            raise PermissionError(
                f"Workflow {self.workflow_name!r} is not permitted to {permission.value}."
            )


FILING_ANALYSIS_IDENTITY = WorkflowIdentity(
    workflow_name="filing-analysis",
    tenant_id="__runtime_scoped__",
    allowed_permissions=frozenset(
        {
            AutomationPermission.retrieve_public_filings,
            AutomationPermission.run_finance_agents,
            AutomationPermission.store_report,
        }
    ),
)


def scoped_filing_analysis_identity(tenant_id: str) -> WorkflowIdentity:
    return FILING_ANALYSIS_IDENTITY.model_copy(update={"tenant_id": tenant_id})
