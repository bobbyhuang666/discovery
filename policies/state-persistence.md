# State Persistence

## Activation

Use persistence when a writable workspace exists and the work may span turns, conversations, models, or parallel workstreams. Store only project-relevant information.

## Files

```text
.discovery/
├── .gitignore
├── state.yaml
├── handoff.json
├── events.jsonl
├── decisions.md
├── context-index.yaml
├── project-ontology.yaml
├── specs/current.yaml
├── changes/
├── archive/
└── workstreams/
```

Create `.discovery/.gitignore` containing `*` and `!.gitignore` to prevent accidental commits.

## Lifecycle

1. Validate existing state against `schemas/state.schema.json`.
2. Compare the project fingerprint with the current workspace.
3. If stale or incompatible, summarize differences before resuming.
4. Write atomically: temporary file, schema validation, backup, replace.
5. Append transitions to `events.jsonl`; never rewrite history.
6. Keep `handoff.json` concise and executable.
7. Keep current truth separate from active changes.
8. Reset or delete session state without deleting project artifacts unless explicitly requested.

## Privacy

Redact credentials, secrets, unrelated personal data, and sensitive raw content that can be referenced by location instead. Do not version `.discovery` unless the user explicitly chooses to.
