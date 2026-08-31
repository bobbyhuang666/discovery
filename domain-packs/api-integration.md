# Domain Pack: API Integration

Load for API-first products, connector work, webhooks, SSO, payments, or service-to-service changes.

## Concern slots

- contract and version ownership;
- authentication and authorization;
- schema, validation, and compatibility;
- retries, idempotency, ordering, and deduplication;
- rate limits and backpressure;
- timeout and partial failure;
- sandbox and test fixtures;
- observability and correlation IDs;
- reconciliation and replay;
- deprecation and rollout.

## Common hidden requirements

- clock skew and expiry;
- webhook signature rotation;
- duplicated or delayed events;
- provider-specific error normalization;
- per-tenant quotas;
- data residency and deletion propagation.

Pair with `auditors/integration.md` and usually `auditors/security.md`.
