# Independent Review Policy

## Purpose

Reduce false PASS verdicts from the same agent that authored the artifact.

## Preferred review

When the platform supports subagents, separate models, or fresh isolated contexts:

1. the author produces the artifact and evidence index;
2. the verifier receives only the artifact, constitution, source references, and validator contract;
3. the verifier checks completeness, consistency, feasibility, testability, and unsupported claims;
4. the verifier returns `PASS`, `CONCERNS`, or `FAIL` with defect IDs;
5. the author repairs defects and re-submits only when needed.

The verifier must not see the author's private reasoning or self-assessment.

## Fallback

If true independence is unavailable, perform a fresh adversarial review and label it **self-review**, never independent review.

## Completion rule

Deep work and high-risk changes require independent review when the runtime can provide it. A review may not be marked PASS while a critical defect remains unresolved.
