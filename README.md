# Discovery v17.1 — Runtime Edition

Discovery is a requirements-discovery Skill with an optional deterministic Python Host Runtime.

## v17.1 focus

v17.1 is a behavioral correction release based on benchmark audit findings:

- clear, tiny, low-risk, reversible work exits Discovery immediately;
- bounded work may ask one material confirmation and then proceed;
- missing tools trigger one capability negotiation, not a repeated file-request loop;
- light models receive a smaller policy bundle and stricter action limits;
- the Host records model tier, actual capabilities, and fallback history.

The state machine, event log, atomic persistence, Living Spec, and policy router from v17 remain intact.

## Install and validate

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m unittest discover -s tests -v
python scripts/validate_skill.py
```

## Triage before starting Discovery

```bash
discovery triage --profile @templates/request-profile.json --json
```

The result is `direct`, `confirm_once`, or `discover`.

## Route the real runtime

```bash
discovery route \
  --intent discover --track change --depth quick \
  --workspace --capabilities none --model-tier light --json
```

See `HOST_RUNTIME.md`, `USAGE.md`, and `TESTING_GUIDE.md`.

## Evaluation status

v17.1 is a runtime candidate. It does not inherit the invalid “world strongest” conclusion from the prior benchmark. Final claims require repaired, tool-fair, multi-judge live evaluation and downstream implementation tests.
