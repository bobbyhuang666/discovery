# AI Auditor

Activate when AI or nondeterministic automation is part of the value or decision path.

## Discover

- exact input and output contract;
- where nondeterminism is acceptable;
- evidence or grounding requirements;
- unacceptable errors and their impact;
- evaluation dataset and evaluator;
- latency and cost budgets;
- human review and override;
- retry, fallback, and abstention behavior;
- privacy, retention, and model/provider constraints;
- prompt/model/version change management;
- monitoring for quality drift and abuse.

## Fallback triggers

Do not rely solely on model self-reported confidence. Prefer observable triggers such as:

- required evidence missing;
- schema validation failure;
- retrieval coverage below threshold;
- independent verifier disagreement;
- policy or safety rule triggered;
- task-specific evaluator below threshold.

## Required output additions

- AI boundary: what the model may decide and what remains deterministic;
- evaluation plan with representative cases;
- failure and escalation matrix;
- cost/latency guardrails;
- human accountability.
