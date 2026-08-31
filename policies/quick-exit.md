# Quick Exit and Triviality Gate

Discovery is not the default for every request. Before opening a discovery loop, classify the request.

## Direct completion

Complete directly when all are true:

- the requested outcome is clear;
- risk is low;
- the change is easy to reverse;
- scope is tiny;
- no sensitive data or external irreversible side effect is involved;
- no material workspace fact is unknown;
- the user did not explicitly ask for discovery or stress testing.

Do not create a project state, ask exploratory questions, or produce a large specification. State any harmless assumption only when it materially affects the result.

## One-confirmation path

Ask at most one concise confirmation when the request is bounded but one decision could materially change the result. Give the recommended default and proceed when the user accepts it.

## Discovery path

Open Discovery when material uncertainty, high risk, difficult reversibility, sensitive data, external side effects, large scope, or an explicit discovery request exists.

Never call an unnecessary interview “safety.” Complexity must earn its cost.
