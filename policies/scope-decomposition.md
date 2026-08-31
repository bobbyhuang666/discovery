# Scope Decomposition Policy

## Goal

Detect when a request contains multiple independently valuable or independently deployable systems before detailed discovery creates one unimplementable specification.

## Decomposition signals

Decompose when two or more parts have different:

- primary actors or decision owners;
- release or validation paths;
- data boundaries or security posture;
- failure domains;
- success signals;
- implementation teams or workstreams;
- ability to deliver value independently.

Do not decompose merely because a feature has several internal components.

## Procedure

1. Name the candidate workstreams.
2. Explain the seams and dependencies.
3. Identify the smallest workstream that proves or delivers the core value.
4. Record shared principles and cross-workstream contracts.
5. Run discovery on one workstream at a time unless workshop mode is explicitly selected.

## Output

```yaml
scope_decomposition:
  decision: single_spec | split
  rationale: ""
  workstreams:
    - id: WS-001
      outcome: ""
      actors: []
      depends_on: []
      shared_contracts: []
  first_workstream: WS-001
```
