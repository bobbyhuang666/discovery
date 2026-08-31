# Execution Alignment Handoff

Use after a discovery artifact exists and an implementation plan, architecture proposal, prototype, or completed implementation is available.

## Review questions

- Does every P0 behavior appear in the plan or implementation?
- Did the executor introduce behavior that conflicts with a decision, constraint, or non-goal?
- Are defaults being mistaken for confirmed requirements?
- Are acceptance tests at an observable behavior seam?
- Are migration, security, data, and operational commitments represented where required?
- Did implementation evidence invalidate a discovery assumption?
- Are new unknowns routed back to the correct decision owner?

## Output

```yaml
alignment_review:
  covered: []
  missing: []
  misinterpreted: []
  scope_added_without_decision: []
  assumptions_invalidated: []
  recommended_changes: []
  readiness: pass | revise | blocked
```

Do not rewrite the implementation merely because it differs internally from an early suggestion. Judge externally required behavior, constraints, risks, and accepted decisions.
