# Discovery v17.1 Release Review

## Verdict

**Controlled evaluation candidate.** The release fixes three behavior defects identified in the audited benchmark, but it does not claim the benchmark's reported ranking or “world strongest” verdict.

## Changes accepted

1. **Quick Exit** — clear, tiny, low-risk, reversible requests bypass Discovery; bounded requests may ask one confirmation.
2. **Capability Negotiation** — missing tools produce one explicit fallback with upload, paste, or assumption paths; repeated fallback is rejected by the Host.
3. **Light-Model Contract** — one visible question, at most three options, three files, and three state events; compact visible output.

## What is code-enforced

- deterministic triage from a structured request profile;
- capability-aware policy routing;
- unavailable inspect/research action rejection;
- one-time capability fallback history;
- model-tier-specific action validation;
- state transition and invariant enforcement;
- atomic persistence and recovery.

## What remains unproven

- that Quick Exit improves real user satisfaction without missing material uncertainty;
- that light-model constraints increase hidden-requirement recall;
- that deterministic Host mode beats prompt fallback on the four target models;
- that Discovery reduces downstream clarification and rework;
- that it outperforms executable competitor workflows under equal tools.

## Release decision

Ship v17.1 for the repaired blind-test round. Freeze the core methodology until the evaluation harness itself is corrected.
