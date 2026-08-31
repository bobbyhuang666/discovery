# Evaluation Corpus

`cases.json` checks deterministic routing policy. `interview-scenarios.json` defines oracle-backed multi-turn situations with hidden requirements, inspectable facts, decision-only information, and stop conditions.

A model run should be annotated using `schemas/eval-run.schema.json`. Then score it:

```bash
python scripts/score_transcript.py --run path/to/run.json
```

Compare at least:

1. base model without Discovery;
2. previous released skill;
3. current core only;
4. current full system.

Keep a held-out scenario set. Do not tune solely against public cases.
