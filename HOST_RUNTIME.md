# Discovery v17.1 Host Runtime

The Host is an optional deterministic control plane. Prompt fallback remains portable but cannot guarantee state consistency.

## Responsibilities

- request triage before entering Discovery;
- policy routing under context budgets;
- capability-aware action guards;
- light-model interaction limits;
- legal state transitions and invariant enforcement;
- structured event application;
- atomic writes, locks, pending-event recovery, and append-only logs.

## Install

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --requirement requirements.lock
python -m pip install --no-deps -e .
```

## Initialize runtime facts

```bash
python scripts/init_state.py \
  --workspace . --project-id demo \
  --intent discover --track build --depth quick \
  --model-tier light \
  --capabilities filesystem,command_execution,persistence
```

Use `--capabilities none` for chat-only execution. Capabilities describe what the current harness can actually do.

## One-time fallback enforcement

An LLM action may set `capability_fallback` when explaining a missing capability. The Host records the capability and rejects a second identical fallback, preventing repeated “please upload the file” loops.

## Transaction protocol

1. Acquire the state lock.
2. Recover any previously committed pending event.
3. Validate the action against the model and capability profile.
4. Apply and validate state events.
5. Write `pending-event.json`.
6. Atomically replace `state.yaml`.
7. Append the event with revisions and state hash.
8. Remove the pending record.
