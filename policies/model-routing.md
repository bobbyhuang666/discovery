# Model Routing and Failure Escalation

## Goal

Use the least expensive capable model for each bounded action while escalating when quality or risk requires it.

## Profiles

| Profile | Suitable work |
|---|---|
| routine | parsing, formatting, low-risk extraction, deterministic checks |
| reasoning | decision graphs, conflict resolution, trade-off analysis, complex synthesis |
| research | source retrieval, freshness-sensitive comparison, evidence synthesis |
| verifier | adversarial review, unsupported-claim detection, readiness judgment |
| visual | mockups, diagrams, image interpretation, spatial comparison |

## Escalation triggers

Escalate to a stronger or specialized model when:

- two attempts produce the same unresolved defect;
- evidence conflicts and the decision is high-impact;
- the model invents unsupported claims or fails a schema twice;
- a safety, legal, financial, or irreversible-data decision is involved;
- a verifier disagrees with the author on a critical defect;
- the context cannot be reduced without losing load-bearing evidence.

## Independence

When possible, use a different model or isolated context for verification. Record the selected profile, model identifier when available, reason, and result. Never imply that routing occurred when the host runtime cannot perform it.
