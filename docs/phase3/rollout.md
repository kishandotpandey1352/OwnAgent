# Phase 3 rollout

1. Development with flags off by default.
2. CI contracts/unit/integration/security/evaluation gates.
3. Staging with synthetic and approved test data.
4. Internal users / shadow mode.
5. Small canary percentage.
6. Wider rollout only when SLO, cost, grounding and compliance metrics remain healthy.

Flags: `multi_agent_enabled`, `evidence_review_enabled`, `compliance_blocking_enabled`, `automation_enabled`.

Rollback is code/image rollback plus disabling the relevant flag. Automation consumers should be paused before rolling back an incompatible event schema.
