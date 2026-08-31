# Claim Ledger

Use especially in Change and Validate work to prevent inferred system behavior from becoming false specification truth.

```yaml
claim:
  id: CLAIM-001
  statement: "Refunds above ¥5,000 require supervisor approval"
  source_refs: []
  corroboration:
    runtime: false
    test: false
    code: true
    maintained_spec: false
    user_confirmation: false
  status: unverified | corroborated | contradicted | superseded
  gaps: []
```

Code proves implementation, not intent. Tests prove covered behavior, not completeness. User statements prove desired intent, not current runtime behavior. Preserve disagreements until resolved.
