# Domain Pack: Internal Automation

Load for scripts, VBA, scheduled jobs, back-office tools, and workflow automation.

## Concern slots

- trigger and invocation;
- source files/systems and expected variation;
- deterministic business rules;
- duplicate and idempotency behavior;
- partial success and error reporting;
- manual review or correction;
- audit/source traceability;
- runtime environment and permissions;
- scheduling and concurrency;
- maintenance owner;
- acceptance fixtures using representative real inputs.

## Common hidden requirements

- source filename and row-level provenance;
- tolerance for missing columns and malformed data;
- rerun behavior without duplication;
- locked/open file handling;
- locale, date, currency, and encoding differences;
- logs that a non-developer can understand.

Do not require commercialization or retention analysis.
