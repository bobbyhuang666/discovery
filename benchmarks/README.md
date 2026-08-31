# Static Protocol Coverage Audit

This benchmark compares explicit workflow contracts, not popularity and not live model performance. A project receives credit only when a capability is stated operationally in the reviewed source artifact.

## Compared systems

- Superpowers Brainstorming
- Matt Pocock Grilling
- GitHub Spec Kit
- OpenSpec
- BMad Method
- GSD
- Discovery v15 baseline
- Discovery v17.1 candidate

## Limits

- Static protocol coverage cannot prove question quality, implementation success, or user satisfaction.
- Repository popularity is deliberately excluded from scoring.
- Profiles are manually evidence-coded and should be independently reviewed when source versions change.
- The live interview benchmark under `evals/` remains the decisive next step.

Run:

```bash
python scripts/run_protocol_benchmark.py
```
