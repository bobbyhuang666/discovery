# Question Lookahead

Use for important candidate questions before consuming user attention.

## Purpose

Prefer questions whose plausible answers lead to meaningfully different decisions, requirements, risks, or experiments.

## Candidate record

```yaml
candidate:
  question: ""
  decision_id: D-001
  plausible_branches:
    - answer: "A"
      changed_decisions: []
      changed_requirements: []
      changed_risks: []
  dependency_unblocking: high | medium | low
  expected_information_value: high | medium | low
  user_effort: high | medium | low
  redundancy_risk: high | medium | low
  can_inspect_instead: false
```

## Selection

Reject or defer a question when:

- plausible answers would not alter the next action;
- the answer is already available through inspection or testing;
- an unresolved upstream decision makes every answer premature;
- it repeats a prior question without new evidence;
- it concerns a low-impact reversible detail that can be defaulted.

When two questions are similar, prefer the one that unblocks more downstream decisions with less user effort.
