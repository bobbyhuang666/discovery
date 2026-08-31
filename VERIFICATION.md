# Verification Report

Generated automatically. Do not edit by hand.

- **Status:** PASS
- **Generated at:** 2026-07-27T15:06:49.881873+00:00
- **Markdown files:** 87
- **Total Markdown lines:** 2576
- **SKILL.md lines:** 106
- **Automated checks:** 5

## Runtime unit tests

```text
test_light_rejects_multiple_questions (test_runtime.ContractTests.test_light_rejects_multiple_questions) ... ok
test_light_rejects_too_many_options (test_runtime.ContractTests.test_light_rejects_too_many_options) ... ok
test_standard_allows_four_options (test_runtime.ContractTests.test_standard_allows_four_options) ... ok
test_action_guard_and_revision (test_runtime.HostTests.test_action_guard_and_revision) ... ok
test_capability_fallback_only_once (test_runtime.HostTests.test_capability_fallback_only_once) ... ok
test_light_contract_enforced_by_host (test_runtime.HostTests.test_light_contract_enforced_by_host) ... ok
test_missing_inspection_capability_rejected (test_runtime.HostTests.test_missing_inspection_capability_rejected) ... ok
test_pending_log_recovery (test_runtime.HostTests.test_pending_log_recovery) ... ok
test_available_workspace_capability_routes_inspection (test_runtime.RouterTests.test_available_workspace_capability_routes_inspection) ... ok
test_context_budget (test_runtime.RouterTests.test_context_budget) ... ok
test_deep_risk_routing (test_runtime.RouterTests.test_deep_risk_routing) ... ok
test_light_model_bundle (test_runtime.RouterTests.test_light_model_bundle) ... ok
test_missing_workspace_capability_routes_fallback (test_runtime.RouterTests.test_missing_workspace_capability_routes_fallback) ... ok
test_quick_is_pruned (test_runtime.RouterTests.test_quick_is_pruned) ... ok
test_blocking_decision_rejects_ready (test_runtime.StateTests.test_blocking_decision_rejects_ready) ... ok
test_budget_enforced (test_runtime.StateTests.test_budget_enforced) ... ok
test_event_resolution (test_runtime.StateTests.test_event_resolution) ... ok
test_illegal_transition (test_runtime.StateTests.test_illegal_transition) ... ok
test_bounded_request_confirms_once (test_runtime.TriageTests.test_bounded_request_confirms_once) ... ok
test_clear_tiny_request_exits (test_runtime.TriageTests.test_clear_tiny_request_exits) ... ok
test_explicit_discovery_forces_discovery (test_runtime.TriageTests.test_explicit_discovery_forces_discovery) ... ok
test_high_risk_forces_discovery (test_runtime.TriageTests.test_high_risk_forces_discovery) ... ok

----------------------------------------------------------------------
Ran 22 tests in 0.102s

OK
```

## Structural/schema/smoke

```text
Validated: /mnt/data/discovery_v171_work/discovery
Errors: 0
Warnings: 0
```

## Routing regression

```text
Evaluation cases: 12
Failures: 0
```

## Interview corpus

```text
Interview scenarios: 8
Schema errors: 0
```

## Static protocol coverage audit

```text
Wrote /mnt/data/discovery_v171_work/discovery/benchmarks/results.yaml
Wrote /mnt/data/discovery_v171_work/discovery/benchmarks/RESULTS.md
1. Discovery v17.1: 280/284 (98.6%)
2. GSD: 252/284 (88.7%)
3. BMad Method: 233/284 (82.0%)
4. OpenSpec: 194/284 (68.3%)
5. Discovery v15: 191/284 (67.3%)
6. GitHub Spec Kit: 179/284 (63.0%)
7. Superpowers Brainstorming: 136/284 (47.9%)
8. Matt Pocock Grilling: 65/284 (22.9%)
```
