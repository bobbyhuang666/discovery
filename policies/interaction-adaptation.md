# Interaction Adaptation

## Profile dimensions

```yaml
interaction_profile:
  expertise: novice | mixed | expert
  response_style: brief | detailed | uncertain
  decision_style: wants_options | wants_recommendation | wants_control
  channel: realtime | async | cli | workshop
  fatigue: low | medium | high
```

## Adaptation rules

- **Novice:** use concrete examples, plain language, and recommended defaults.
- **Expert:** skip basic definitions and ask about boundaries, invariants, failure modes, and trade-offs.
- **Brief answers:** narrow to the most blocking decision and offer selectable options.
- **Uncertain answers:** create a sketch, prototype, or comparison instead of repeatedly asking abstract questions.
- **Wants recommendation:** state the best current option and reversal conditions.
- **Wants control:** present evidence and alternatives without silently defaulting.
- **Async:** one decision may include up to three tightly coupled fields to reduce round trips.
- **Fatigue:** stop optional exploration, summarize, and resolve only high-risk blockers.

## Checkpoints

Provide a concise checkpoint every 3–5 turns or after a major decision:

- what is confirmed;
- what changed;
- the highest-risk remaining item;
- what happens next.

Do not dump the full internal state every turn.
