# ADR-003: Phase 3 Governed Agent Runtime Foundation

**Status:** Accepted for 3I-A  
**Decision date:** 2026-08-31  
**Scope:** Phase 3I, with compatibility requirements for 3J and 3K

## Context

The current product is a single LangGraph workflow with a safe server-owned tool registry. Phase 3I introduces multiple specialist agents without replacing the proven document RAG, financial fact extraction, CSV analysis, deterministic calculator, chart planner, or Phase 3H Serper web fallback.

The new runtime must remain bounded, evidence-first, auditable, tenant/user scoped, cost controlled, and backward compatible with the existing `/agents/analyze` path until the multi-agent runtime is proven.

## Decisions

1. **3I-A defines contracts and policy only.** It does not change `/agents/analyze`, the existing LangGraph graph, or frontend behavior.
2. **All inter-agent messages use versioned Pydantic contracts.** Core execution data must not be represented only as arbitrary dictionaries.
3. **Only server-registered agents are valid.** User/model text can never invent or name an unregistered executable agent.
4. **The existing `TOOL_REGISTRY` remains the lower-level tool authority.** Agent permissions reference the existing `ToolName` enum so tool names cannot drift.
5. **Agents are least privilege.** Each agent has explicit capabilities, tools, network/data permissions, LLM requirement, timeout, retry ceiling, and cost ceiling.
6. **No agent can call another agent directly.** Only the future coordinator/executor may schedule registered agents through a validated DAG.
7. **Web research remains permission gated.** `web_research_agent` is the only 3I agent with restricted public-network access, and it still requires `allow_web_fallback=true` at execution time.
8. **Evidence is a first-class contract.** Financial values use `Decimal` where normalized numeric precision matters, preserve source references, and support deterministic calculation lineage.
9. **Execution limits are configuration driven.** Operational defaults live in `app/core/config.py`; future 3I-C/3I-D code must not duplicate them as hidden constants.
10. **Tenant/user identity travels in `ExecutionContext`.** Every future adapter and executor must pass these identifiers to existing user-scoped services.
11. **Feature rollout is off by default.** `multi_agent_enabled=false` until coordinator, DAG, evidence review, security, regression, and rollout gates pass.
12. **3J/3K compatibility is reserved now.** Contracts expose request/plan/task identifiers, schema versions, agent versions, timestamps, cost, latency, and evidence lineage required for later audit/tracing/event workflows.

## Security boundaries

- External content remains untrusted input.
- Only `web_research_agent` may have network access.
- `answer_composer` and `evidence_review_agent` have no tool access.
- `calculation_agent` is deterministic and has no network/LLM access.
- Agent definitions are immutable at runtime.
- The registry validates that every permitted tool actually exists in `TOOL_REGISTRY`.
- Recursive agent invocation is prohibited.

## 3I-A non-goals

- No coordinator prompt.
- No plan/DAG policy validator beyond structural schema validation.
- No parallel execution.
- No specialist wrappers yet.
- No public API response migration.
- No frontend multi-agent UI.
- No replacement of Phase 3H components.

## Consequences

This adds a second, typed orchestration boundary alongside the existing single-agent path. It intentionally increases schema/policy code before adding coordinator intelligence. That is preferred because future routing, execution, audit, compliance, and automation can share stable contracts rather than introducing incompatible payloads later.

## Next release

3I-B creates thin specialist wrappers around the existing tools and proves that all Phase 3H regression tests remain green.
