import pytest

from app.agents.security.legacy_runtime import (
    LegacyToolAuthorizationError,
    authorize_legacy_tool,
    build_legacy_execution_context,
    require_legacy_tool_authorization,
)
from app.agents.security.permissions import (
    ToolAuthorizationStatus,
)
from app.schemas.tools import ToolName


def make_state(**overrides):
    state = {
        "request_id": "legacy-request-1",
        "user_id": "legacy-user-1",
        "provider_id": None,

        "use_documents": False,
        "document_ids": [],
        "top_k": 6,

        "dataset_id": None,

        "allow_web_fallback": False,
        "trusted_web_domains": [],

        "granted_permissions": [],
    }

    state.update(overrides)

    return state


def test_legacy_document_search_denied_without_scope():
    context = build_legacy_execution_context(
        make_state()
    )

    decision = authorize_legacy_tool(
        tool_name=ToolName.document_search,
        context=context,
    )

    assert (
        decision.status
        == ToolAuthorizationStatus.deny
    )


def test_legacy_document_search_allowed_with_scope():
    context = build_legacy_execution_context(
        make_state(
            use_documents=True,
            document_ids=["doc-1"],
        )
    )

    decision = authorize_legacy_tool(
        tool_name=ToolName.document_search,
        context=context,
    )

    assert (
        decision.status
        == ToolAuthorizationStatus.allow
    )


def test_legacy_dataset_tool_allowed_with_dataset():
    context = build_legacy_execution_context(
        make_state(
            dataset_id="dataset-1",
        )
    )

    decision = authorize_legacy_tool(
        tool_name=ToolName.csv_profile,
        context=context,
    )

    assert (
        decision.status
        == ToolAuthorizationStatus.allow
    )


def test_legacy_web_denied_without_permission():
    context = build_legacy_execution_context(
        make_state()
    )

    decision = authorize_legacy_tool(
        tool_name=ToolName.web_research,
        context=context,
    )

    assert (
        decision.status
        == ToolAuthorizationStatus.deny
    )


def test_legacy_web_allowed_with_legacy_scope():
    context = build_legacy_execution_context(
        make_state(
            allow_web_fallback=True,
        )
    )

    decision = authorize_legacy_tool(
        tool_name=ToolName.web_research,
        context=context,
    )

    assert (
        decision.status
        == ToolAuthorizationStatus.allow
    )


def test_legacy_calculator_requires_no_external_permission():
    context = build_legacy_execution_context(
        make_state()
    )

    decision = authorize_legacy_tool(
        tool_name=ToolName.financial_calculator,
        context=context,
    )

    assert (
        decision.status
        == ToolAuthorizationStatus.allow
    )


def test_legacy_require_authorization_fails_closed():
    context = build_legacy_execution_context(
        make_state()
    )

    with pytest.raises(
        LegacyToolAuthorizationError,
        match="TOOL_POLICY_DENIED",
    ):
        require_legacy_tool_authorization(
            tool_name=ToolName.document_search,
            context=context,
        )