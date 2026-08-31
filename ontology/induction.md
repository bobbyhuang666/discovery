# Project Concern Tree Induction

## Goal

Build a project-specific coverage map instead of asking a static universal checklist.

## Inputs

1. Selected track and domain-pack seeds.
2. Existing specifications, ADRs, issues, tests, schemas, code, and operational artifacts.
3. User language and accepted domain vocabulary.
4. External standards only when relevant.

## Procedure

1. Start from relevant domain-pack aspects and dimensions.
2. Merge equivalent concepts using project terminology.
3. Expand dimensions when project evidence reveals additional states, roles, interfaces, or failures.
4. Add a new aspect only when it cannot fit an existing structure without distortion.
5. Link each slot to evidence, decisions, requirements, or a `not_applicable` rationale.
6. Save to `templates/project-ontology.yaml` format when persistence is enabled.

## Coverage states

- `untouched`
- `partial`
- `covered`
- `not_applicable`
- `deferred`

The tree is a navigation aid, not a completeness score. A covered slot may still contain weak evidence.
