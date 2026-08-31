# Implementation Readiness Validator

Return exactly one readiness verdict:

- `PASS`: implementation can begin with no unresolved blocking decision;
- `CONCERNS`: implementation may begin only with the listed controlled risks or deferred decisions;
- `FAIL`: implementation would require guessing about a high-impact decision, violate a principle, or lack testable P0 behavior.

## Checks

### Intent and scope

- The outcome and non-goals are explicit.
- Scope is small enough for one implementation contract or has been decomposed.

### Authority and principles

- Required approvals are recorded.
- No requirement or approach conflicts with an active constitutional principle.

### Behavior and tests

- Every P0 behavior has observable acceptance criteria.
- Error, empty, cancellation, and recovery behavior are covered where material.

### Evidence and uncertainty

- Load-bearing claims have provenance.
- High-impact assumptions are verified, explicitly accepted, or converted into experiments.
- Deferred items do not silently block implementation.

### Delivery

- Data, integration, migration, security, rollout, and operations are represented at the selected depth.
- The implementation plan preserves requirement IDs and acceptance seams.

## Output

```yaml
implementation_readiness:
  verdict: PASS | CONCERNS | FAIL
  blocking_defects: []
  controlled_risks: []
  missing_evidence: []
  required_approvals: []
  next_action: ""
```
