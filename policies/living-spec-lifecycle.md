# Living Specification Lifecycle

## Separation of truth and proposal

```text
.discovery/specs/current.yaml       current accepted truth
.discovery/changes/<change-id>/     proposed or in-progress delta
.discovery/archive/<change-id>/     verified historical change
```

Never edit current truth merely because a proposal exists.

## Change lifecycle

`proposed -> approved -> in_progress -> implemented -> verified -> archived`

Alternative terminal states: `rejected`, `superseded`.

## Required change artifacts

- `proposal.yaml`: rationale, scope, decision owner, intended outcome.
- `delta.yaml`: add, modify, remove, and preserve operations using stable IDs.
- `impact.yaml`: affected actors, requirements, data, interfaces, tests, operations, and risks.
- `verification.yaml`: acceptance and regression evidence.

## Merge and archive

A change may be archived only when:

1. its status is `verified`;
2. current specification has been updated with the accepted delta;
3. stable IDs and supersession links are preserved;
4. the current specification records the applied change ID;
5. validation passes.

The scripts initialize and validate this structure; semantic merging remains an explicit agent or human decision.
