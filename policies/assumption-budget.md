# Assumption Budget

## Purpose

Control uncertainty without trapping the user in endless discovery.

## Assumption record

```yaml
assumption:
  id: A-001
  statement: "Most imports contain fewer than 5,000 rows"
  impact: medium
  reversibility: easy
  cost_of_being_wrong: medium
  source: derived
  treatment: test_during_implementation
  owner: engineering
  revisit_condition: "Performance test exceeds 10 seconds"
```

## Treatment matrix

| Impact | Reversibility | Treatment |
|---|---|---|
| High | Hard | Validate, research, or experiment before commitment |
| High | Easy | Use a documented default and validate early |
| Low | Hard | Confirm if irreversible harm remains plausible |
| Low | Easy | Default without asking unless preference-sensitive |

## Allowed treatments

- validate now;
- inspect artifact;
- run experiment;
- use explicit default;
- assign owner and deadline;
- defer with revisit condition;
- accept as an exploratory risk.

## Readiness rule

A spec may contain unknowns and assumptions. It may not contain an untreated high-impact, hard-to-reverse assumption that blocks the next stage.

Never use “no assumptions remain” as a gate. Never hide assumptions to make a document look complete.
