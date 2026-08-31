# Next Action Selector

Discovery chooses the cheapest reliable action that can change an important decision.

## Action types

| Action | Use when | Example |
|---|---|---|
| ASK | Only the user or decision owner can answer | priority, preference, authority, acceptable trade-off |
| INSPECT | The environment contains the fact | framework, API behavior, current UI, schema, tests |
| RESEARCH | A current external fact is required | regulation, vendor limit, industry standard |
| TEST | Behavior or feasibility can be observed | latency, import quality, API error behavior |
| SKETCH | Structure is hard to confirm abstractly | workflow, state machine, permission matrix |
| PROTOTYPE | Preference or interaction needs a criticizable artifact | UI concept, sample output, API stub |
| DEFAULT | The choice is low-impact and reversible | labels, minor ordering, internal naming |
| SUMMARIZE | Shared understanding needs compression | checkpoint after several decisions |
| VALIDATE | A proposed interpretation or artifact needs confirmation | AS-IS/TO-BE, acceptance criteria |
| STOP | Additional discovery has lower value than the next stage | ready for experiment, spec, or implementation |

## Selection questions

Before acting, ask internally:

1. Will the result change a requirement, risk, priority, or next-stage decision?
2. Can the fact be inspected or tested instead of asked?
3. Is the decision important enough to consume user attention?
4. Is there a safer reversible default?
5. Does another unresolved decision block this one?
6. Would a sketch or prototype produce more reliable feedback than prose?

## Tie-breaking

Prefer, in order:

1. risk reduction;
2. dependency unblocking;
3. direct evidence;
4. lower user effort;
5. lower execution cost.

## Anti-patterns

- Asking a user which framework the existing repository uses.
- Researching a personal preference that only the user can decide.
- Prototyping before the core problem or decision is known.
- Continuing to ask after the stop policy is satisfied.
