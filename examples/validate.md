# Example: Validate a Change Proposal

**User:** Check whether this database migration proposal is ready.

**Route:** Validate / Change / Deep.

**Correct action:** Verify current-schema claims, migration invariants, rollback, data reconciliation, and regression evidence. Return blocking and non-blocking findings.

**Bad action:** Rewrite the proposal into a preferred architecture without identifying defects in the supplied plan.
