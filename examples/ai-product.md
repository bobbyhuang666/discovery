# Example: AI Product

**User:** The AI should automatically approve expense claims.

**Correct route:** Build / Deep with AI, data, integration, security, and operations auditors.

**Upstream decision:** Which claims may be auto-approved, and which require deterministic rules or human review?

**Recommendation:**

> **Recommendation:** Keep policy eligibility deterministic and use AI only to extract and explain evidence. Auto-approve only when deterministic checks pass and required documents are present. Route ambiguity, policy exceptions, and high-value claims to a human. Expand autonomy only after an evaluation set shows acceptable false-approval risk.

Required discovery includes evaluation data, audit trail, fallback triggers, appeal flow, cost/latency, privacy, and drift monitoring.

**Bad behavior:** Use the model's self-reported confidence as the sole approval threshold.
