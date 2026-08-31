# Artifact Graph and Fluid Actions

## Principle

Artifacts enable actions; they do not trap work in a rigid waterfall. At every step, show which actions are available, blocked, or optional based on evidence and artifact dependencies.

## Core artifacts

- project constitution;
- current living specification;
- concern tree and coverage map;
- decision records;
- change proposal and delta;
- verification evidence;
- implementation readiness report;
- handoff.

## Dependency examples

```yaml
artifact_graph:
  current_spec:
    status: available
    enables: [refine, validate, propose_change]
  change_proposal:
    status: missing
    requires: [current_spec, decision_owner]
    enables: [design_delta, impact_analysis]
  verification:
    status: blocked
    requires: [implemented_change, acceptance_evidence]
    enables: [merge_current_truth, archive]
```

## Rules

1. Recommend the best next action, but expose safe alternatives when useful.
2. Exploration may create no durable artifact when conversation alone is sufficient.
3. A user who already knows the desired outcome may skip exploration.
4. Return to earlier artifacts when new evidence invalidates them.
5. Do not merge a proposal into current truth before verification.
