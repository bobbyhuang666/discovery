# Evidence Management

## Purpose

Keep facts, claims, derivations, and preferences distinct.

## Provenance types

- `user_confirmation`
- `observed_behavior`
- `runtime_test`
- `code_or_schema`
- `maintained_artifact`
- `unverified_artifact`
- `contract_or_policy`
- `external_research`
- `data_analysis`
- `expert_derivation`

## Status

| Status | Meaning |
|---|---|
| confirmed | Directly confirmed by the authorized source or strong observation |
| corroborated | Supported by more than one independent source |
| derived | Reasoned from evidence but not directly confirmed |
| assumed | Temporarily accepted for progress |
| unknown | No reliable basis yet |
| contradicted | Credible sources disagree |
| superseded | Replaced by a later decision or fact |

## Evidence record

```yaml
evidence:
  id: E-001
  claim: "The current import rejects duplicate invoice numbers"
  source_type: runtime_test
  source_ref: "tests/import_duplicates"
  status: confirmed
  observed_at: "2026-07-27"
  applies_to: [REQ-004]
```

## Opportunity profile

Opportunity evidence is multidimensional. Track separately:

- problem reality;
- frequency or trigger;
- impact;
- current alternatives;
- willingness to change or commit;
- decision authority;
- solution fit;
- feasibility;
- commercial viability when relevant.

Do not compress these into one fake precision score.

## Conflict rule

When documentation, code, tests, and user statements disagree, preserve all sources, mark the claim contradicted, and select INSPECT, TEST, or ASK based on what can resolve it.
