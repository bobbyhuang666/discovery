# Domain Pack: AI Product

Load when AI is central to product behavior, not merely a hidden implementation detail.

## Concern slots

- deterministic versus model-controlled boundary;
- grounding and allowed knowledge sources;
- evaluation set and quality thresholds;
- unacceptable error taxonomy;
- abstention, fallback, and human review;
- prompt/model/version governance;
- latency, token, and cost budgets;
- privacy and data retention;
- auditability and explanation needs;
- drift, abuse, and incident response.

## Common hidden requirements

- consistency across retries and users;
- recovery when tools or retrieval fail;
- user correction feeding back into state;
- model-provider substitution;
- evaluation of multilingual or multimodal inputs;
- ownership of harmful or costly decisions.

Always pair with `auditors/ai.md`; add security, data, integration, and operations auditors as relevant.
