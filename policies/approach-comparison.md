# Approach Comparison Policy

## Goal

For a meaningful solution or design decision, present alternatives before locking a direction. The purpose is to expose trade-offs, not to manufacture choices where only one valid answer exists.

## Trigger

Use when a decision is high-impact, difficult to reverse, or materially changes scope, architecture, workflow, risk, or operating cost.

## Method

1. Generate two or three genuinely distinct approaches.
2. Remove options that violate the constitution or hard constraints.
3. Compare each approach on the dimensions that matter for this project.
4. Lead with the recommended approach and explain why.
5. State reversal conditions that would make another option preferable.
6. Record rejected alternatives and rationale when the decision is load-bearing.

## Comparison format

```markdown
### Approach decision: <topic>

**Recommendation:** Approach A — <reason>

| Approach | Core idea | Advantages | Costs and risks | Choose when |
|---|---|---|---|---|
| A | | | | |
| B | | | | |
| C | | | | |

**Reconsider the recommendation when:** <conditions>
```

## Anti-patterns

- Three cosmetic variations of the same approach.
- Presenting the favored answer as neutral fact.
- Comparing technology before the required behavior is understood.
- Asking the user to choose without a recommendation when evidence supports one.
