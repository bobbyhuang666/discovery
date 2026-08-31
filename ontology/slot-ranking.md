# Concern Slot Ranking

Rank unresolved slots using decision value rather than checklist order.

## Signals

- linked high-impact decision;
- difficult reversibility;
- number of blocked requirements or decisions;
- safety, legal, money, privacy, or irreversible data exposure;
- weak evidence for a P0 behavior;
- contradiction between sources;
- expected answer branching value;
- user effort and fatigue;
- availability of inspection or testing instead of asking.

## Rule

A slot with high coverage value but no effect on the next-stage decision may be deferred. A narrow slot that blocks a critical invariant should be handled immediately.
