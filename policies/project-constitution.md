# Project Constitution Policy

## Purpose

Keep durable principles separate from feature requirements and implementation preferences. A constitution protects decisions that must remain true across specifications, changes, plans, and implementations.

## When to use

Create or load a constitution when any of the following applies:

- an existing workspace has stable architecture, security, privacy, legal, brand, or operating rules;
- several changes or workstreams must stay aligned;
- the same constraint repeatedly appears in decisions;
- a violation would create high-cost rework, contractual exposure, unsafe behavior, or irreversible data impact.

Quick disposable work may mark the constitution `not_applicable` with a reason.

## Principle record

```yaml
principle:
  id: PRINCIPLE-001
  statement: "Customer content must not be sent to third-party models"
  rationale: "Contractual data-handling restriction"
  authority: "security_owner"
  status: active
  applies_to: [requirements, design, implementation, operations]
  verification: "Architecture and integration review"
  provenance_refs: [EV-004]
  amendment_rule: "Security owner approval"
```

## Rules

1. Inspect an existing constitution before asking about already-decided principles.
2. Do not turn temporary preferences into constitutional rules.
3. Every active principle needs an authority and an amendment rule.
4. Specifications, changes, and plans must record any relevant principle IDs.
5. A proposed violation is a conflict, not an ordinary assumption.
6. Amend rather than silently overwrite; preserve superseded principles and rationale.
