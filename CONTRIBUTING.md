# Contributing

## Principles

- Add a module only when it changes measurable behavior or downstream outcomes.
- Keep current truth separate from proposed change.
- Preserve stable IDs in living specifications.
- Add or update evaluation scenarios for every material policy change.
- Do not claim production readiness or superiority from structural tests alone.

## Required checks

```bash
python scripts/validate_skill.py
python scripts/run_evals.py
python scripts/validate_eval_corpus.py
python scripts/generate_verification.py
```

New interview policies should include a scenario demonstrating the failure they prevent and a held-out test before release.
