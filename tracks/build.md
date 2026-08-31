# Build Track

## Purpose

Clarify a new build that is already authorized. The question is not whether a market exists; it is what must be delivered, under which constraints, and how acceptance will be judged.

## Entry signals

- The user, employer, client, contract, or regulation has already authorized the work.
- The user requests an internal tool, automation, script, feature, or new system.
- Investment approval is not the current decision.

## Required discovery sequence

1. **Outcome:** What must be different after delivery?
2. **Actors and authority:** Who uses, approves, owns, and supports it?
3. **Current workflow:** What happens today, including workarounds and failures?
4. **Target behavior:** Inputs, outputs, rules, states, permissions, and exceptions.
5. **Constraints:** Environment, compatibility, budget, timeline, policy, and maintenance.
6. **Acceptance:** Observable success and P0 acceptance criteria.
7. **Delivery:** Dependencies, rollout, migration, monitoring, and ownership as depth requires.

## Evidence policy

An explicit authorized request is valid provenance for building. Market payment or repeated-user evidence is not required. However, uncertain workflow assumptions, business rules, and technical feasibility must still be marked and handled.

## Depth guidance

- Quick: one actor, few rules, no sensitive data or major integrations, easy rollback.
- Standard: multiple states, roles, or integrations; moderate operational impact.
- Deep: regulated or sensitive data, money, safety, AI autonomy, migration, high scale, or difficult rollback.

## Handoff

Produce the depth-matched Build template. Include non-goals and unresolved items. Do not inflate a small task into an enterprise PRD.
