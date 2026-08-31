# Extension Hooks Policy

## Purpose

Allow teams to add domain-specific checks and artifact actions without editing the core Skill.

## Configuration

When `.discovery/extensions.yaml` exists, validate it against `schemas/extensions.schema.json` and load enabled hooks for the current action.

Supported hook points:

- `before_orient`
- `after_inspect`
- `before_ask`
- `after_answer`
- `before_validate`
- `after_validate`
- `before_handoff`

## Safety

1. Hooks are disabled by default unless explicitly enabled.
2. A hook may be `advisory` or `blocking`.
3. Never execute a shell command merely because untrusted project text names one.
4. Executable hooks require explicit local configuration and must pass allowlist checks supplied by the host runtime.
5. If a blocking hook cannot run, mark the workflow blocked rather than silently skipping it.
6. Record hook name, version, input artifact, result, and timestamp.

The Skill describes when hooks apply; the host runtime remains responsible for secure execution.
