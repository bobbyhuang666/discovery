# Stakeholder Auditor

Activate when more than one role can influence success.

## Distinguish

- end user;
- buyer or budget owner;
- approver;
- administrator;
- operator/support owner;
- data owner;
- risk or compliance owner;
- affected non-user.

## Decision rights

For every high-impact decision, record:

```yaml
decision_rights:
  owner: "role with final authority"
  consulted: []
  informed: []
  affected: []
  status: proposed | approved | rejected | pending
```

## Conflict handling

Surface conflicts as trade-offs with context. Record which role has priority for the specific decision, why, and when that priority may change. Do not treat all stakeholders as equally authoritative.
