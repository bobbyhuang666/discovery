# Domain Pack: Data System

Load for analytics, reporting, ETL, imports, migrations, synchronization, and metric products.

## Concern slots

- source of truth and ownership;
- entities, keys, grain, units, time zones;
- freshness and historical depth;
- completeness, validity, duplicates, and reconciliation;
- schema evolution;
- lineage and metric definitions;
- backfill and migration;
- access, retention, deletion, export;
- late, missing, conflicting, or oversized data;
- reproducible acceptance datasets.

## Common hidden requirements

- slowly changing dimensions;
- retroactive corrections;
- rounding and currency treatment;
- null semantics;
- reprocessing without double counting;
- report numbers matching operational systems.

Pair with `auditors/data.md`; add operations and security when production or sensitive.
