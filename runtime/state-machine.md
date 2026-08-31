# Discovery State Machine

## States

- `orienting`: classify intent, track, depth, authority, and available evidence.
- `discovering`: gather evidence and expose upstream decisions.
- `resolving`: settle conflicts or high-impact choices.
- `awaiting_user`: a decision owner must respond.
- `validating`: test the artifact against gates, evidence, and invariants.
- `ready_for_spec`: enough truth exists to create or update a specification.
- `ready_for_plan`: implementation planning may begin.
- `blocked`: progress requires unavailable authority, evidence, or access.
- `complete`: the current discovery objective is closed.

## Allowed transitions

```text
orienting -> discovering | validating | blocked
discovering -> resolving | awaiting_user | validating | ready_for_spec | blocked
resolving -> discovering | awaiting_user | validating | blocked
awaiting_user -> discovering | resolving | blocked
validating -> discovering | ready_for_spec | ready_for_plan | blocked | complete
ready_for_spec -> validating | ready_for_plan | complete
ready_for_plan -> validating | complete
blocked -> orienting | discovering | complete
```

Never move to `ready_for_plan` while a blocking high-impact decision remains unresolved.
