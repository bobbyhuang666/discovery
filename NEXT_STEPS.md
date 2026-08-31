# Next Steps After v17.1

Do not add more policies before obtaining valid behavioral evidence.

## Next release: Evaluation Integrity, not Discovery feature expansion

Build a separate benchmark runner with:

1. infrastructure retry and `INFRA_FAILURE` separation;
2. deterministic Oracle disclosure rules;
3. separate tool-enabled and chat-only tracks;
4. executable, independently reviewed competitor adapters;
5. two judges plus a third on disagreement;
6. judge/model identity recorded in every score;
7. real transcript-derived user burden metrics;
8. paired bootstrap confidence intervals and reproducible statistics;
9. downstream implementation with acceptance tests and Pass@1;
10. secret scanning and sanitized release artifacts.

## Highest-value experiments

### Experiment A — Quick Exit

Compare v17 and v17.1 on clear low-risk tasks. Measure unnecessary questions, completion accuracy, user words, tokens, and missed constraints.

### Experiment B — Host versus prompt fallback

Run v17.1 Host and portable fallback on each target model. Measure action-schema success, illegal actions, repeated questions, hidden-requirement recall, and context size.

### Experiment C — Light-model contract

Compare `light` and `standard` profiles on the same lightweight models. Verify whether compactness improves adherence without reducing critical discovery.

### Experiment D — Policy ablation

Remove one bundle at a time. Retain a bundle only when its behavioral gain exceeds its context and latency cost.

## Decision rule

- If v17.1 reduces burden without recall loss, retain Quick Exit.
- If light constraints improve adherence but reduce recall, route by task risk rather than model alone.
- If Host mode does not outperform fallback, simplify or remove enforcement that adds no value.
- Only add new methodology after a repeated failure appears across models and scenarios.
