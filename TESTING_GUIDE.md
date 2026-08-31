# Testing Guide

## Runtime and integrity

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/validate_skill.py
```

The runtime suite now covers:

- direct, one-confirmation, and full-discovery triage;
- Quick policy pruning;
- capability-aware routing;
- light-model bundle selection;
- light-model output limits;
- one-time capability fallback;
- unavailable inspection rejection;
- state transitions, budgets, event commits, and recovery.

## Routing and interview corpora

```bash
python scripts/run_evals.py
python scripts/validate_eval_corpus.py
```

## Static protocol audit

```bash
python scripts/run_protocol_audit.py
```

This is gap analysis only. It is not a live benchmark or product ranking.

## Next valid live evaluation

The next benchmark must:

1. separate infrastructure failures from method failures;
2. provide equal tools or use chat-only-compatible scenarios;
3. use executable competitor adapters of equivalent fidelity;
4. use at least two independent judges and a third for disagreement;
5. use deterministic Oracle disclosure rules;
6. measure real user burden from transcripts;
7. run downstream implementation and acceptance tests;
8. evaluate v17.1, not the old v16 chat adapter.
