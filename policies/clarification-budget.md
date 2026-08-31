# Clarification Budget Policy

## Purpose

Resolve the highest-value ambiguities without turning discovery into an endless interview.

## Clarification pass

A clarification pass may ask at most **five accepted questions**. Stop earlier when critical ambiguity is resolved. A retry that only disambiguates the same answer does not consume a new slot.

Before a pass:

1. build a coverage map using `clear`, `partial`, `missing`, `not_applicable`, and `deferred`;
2. generate candidate questions only for partial or missing concerns;
3. exclude facts that can be inspected, tested, or researched;
4. rank candidates by impact, uncertainty, dependency unblocking, and downstream rework risk;
5. keep only the top five.

## Question contract

- Ask exactly one decision theme at a time.
- Prefer 2–5 mutually distinct options when the answer space is discrete.
- Give a recommendation or suggested short answer with brief reasoning.
- Accept `recommended` or `suggested` as explicit approval.
- Do not reveal the remaining queue in advance.

## Incremental integration

After every accepted answer:

1. append the question and answer to the session clarification log;
2. update the affected requirement, decision, constraint, acceptance criterion, or glossary entry;
3. remove or supersede contradictory wording;
4. persist atomically when persistence is enabled;
5. re-evaluate whether remaining questions still matter.

## When the budget ends

Record remaining high-impact ambiguity as deferred with:

- why it matters;
- why it was not resolved;
- owner or evidence needed;
- next safe action.
