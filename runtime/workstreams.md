# Workstreams

Use workstreams when independent areas can progress without sharing unresolved upstream decisions.

## Record

```yaml
workstream:
  id: WS-001
  name: billing-migration
  scope: "Migrate invoice records without changing pricing behavior"
  status: active
  depends_on: []
  owned_decisions: [D-014, D-018]
  owned_requirements: [REQ-031, REQ-032]
  blockers: []
  handoff_ref: ".discovery/workstreams/billing-migration/handoff.json"
```

## Rules

- Do not split tightly coupled decisions into separate workstreams.
- Each requirement and decision has one authoritative owner workstream.
- Shared invariants remain in the current living specification.
- Merge workstream results only after conflict and traceability checks.
