# Workspace Inspection

## Goal

Answer discoverable facts before asking the user while building only the context needed for the current decision.

## Procedure

1. Identify the likely affected area and current intent.
2. Build a shallow map from filenames, manifests, schemas, routes, tests, and recent changes.
3. Read high-signal artifacts first: README, AGENTS, PRD, ADR, package/build manifests, API and data schemas, relevant tests, migrations, configuration, operational notes, and visual references.
4. Inspect only files related to the current decision or concern-tree slot.
5. Record claims and provenance in `context-index.yaml`.
6. Distinguish intended behavior, implemented behavior, tested behavior, and observed runtime behavior.
7. Update the project concern tree using `ontology/induction.md`.
8. Surface contradictions instead of silently choosing a preferred source.

## Evidence rule

Code proves implementation, not necessarily intent. Tests prove covered behavior, not completeness. Documentation is a claim until corroborated. User decisions prove desired intent, not current runtime behavior. Preserve all relevant perspectives.

## Do not

- reorganize the repository during discovery;
- inspect secrets or unrelated files;
- load the entire codebase when bounded inspection is enough;
- ask the user facts that the environment can answer;
- mark a README statement as current truth without corroboration.
