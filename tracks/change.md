# Change Track

## Purpose

Safely modify an existing product, workflow, codebase, integration, or design while preserving required behavior and maintaining current truth separately from proposed change.

## Required sequence

1. **Inspect:** Build a bounded map of relevant documents, code, tests, schemas, configuration, runtime evidence, and recent changes.
2. **Create claims:** Record current-behavior claims using `policies/claim-ledger.md`.
3. **Establish AS-IS:** Corroborate externally observable behavior and identify evidence gaps.
4. **Define TO-BE:** State the desired outcome and deliberate differences.
5. **Compute delta:** Added, removed, modified, preserved, migrated, and out-of-scope behavior.
6. **Trace impact:** Components, interfaces, data, permissions, tests, actors, operations, and documentation.
7. **Protect invariants:** Identify behavior that must not change.
8. **Plan transition:** Compatibility, migration, rollout, monitoring, recovery, and rollback.
9. **Validate:** Define regression and acceptance tests at the highest useful behavior seam.
10. **Maintain lifecycle:** Keep the proposal separate until verified under `policies/living-spec-lifecycle.md`.

## Evidence preference

Prefer reproducible runtime behavior and tests, then current code/schema/configuration, maintained specifications or ADRs, user confirmation, and finally stale documentation. No source alone proves both current behavior and intended behavior.

## Handoff

Produce `templates/change-delta.yaml` and, in durable workspaces, a `templates/change-proposal.yaml`-compatible change package.
