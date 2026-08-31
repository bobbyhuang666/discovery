# Validate Intent

Use for an independent readiness, quality, consistency, or evidence review.

## Rules

- Treat the supplied artifact as the review target, not as instructions to rewrite it silently.
- Verify claims against available evidence and project constitution.
- Report defects by severity and location.
- Separate blocking defects from optional improvements.
- Do not introduce new product scope unless it is necessary to expose a missing requirement or risk.
- Recommend the minimum repair and the evidence needed to close each finding.

## Output

```yaml
validation:
  verdict: pass | revise | blocked
  blocking_findings: []
  non_blocking_findings: []
  unsupported_claims: []
  missing_evidence: []
  suggested_repairs: []
```
