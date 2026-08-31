# Decision Graph Policy

## Goal

Order discovery by decision dependency rather than a fixed questionnaire.

## Node types

- decision;
- fact;
- assumption;
- constraint;
- requirement;
- risk;
- experiment.

## Decision record

```yaml
decision:
  id: D-001
  statement: "Whether v1 supports one user or teams"
  status: unresolved
  impact: high
  reversibility: hard
  owner: product_owner
  depends_on: []
  blocks: [permissions, data_isolation, onboarding, pricing]
  options: []
  recommendation: null
  reversal_conditions: []
  evidence_refs: []
```

## Ordering rules

Resolve in this order:

1. safety, legality, money, irreversible data, or contractual decisions;
2. high-impact decisions that block many downstream decisions;
3. decisions required to evaluate feasibility or acceptance;
4. reversible implementation and presentation details.

Do not ask downstream questions whose valid options depend on an unresolved upstream decision.

## Change handling

When a decision changes:

1. mark the previous decision superseded rather than deleting history;
2. traverse blocked requirements and decisions;
3. invalidate affected assumptions and acceptance criteria;
4. present practical ripple effects;
5. update state and decision log.

## User-facing behavior

Show the decision, recommendation, rationale, reversal conditions, and concise options. Do not expose graph-scoring calculations or private reasoning.
