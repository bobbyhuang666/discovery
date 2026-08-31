---
name: discovery
description: >
  Discover, refine, or validate materially uncertain product, software, workflow, business,
  and existing-system requirements. Use when important uncertainty, risk, evidence gaps,
  stakeholder decisions, or change impact remain. Inspect available artifacts before asking
  discoverable facts. Exit immediately for clear, tiny, low-risk, reversible requests.
compatibility: Portable Agent Skill with an optional deterministic Python host runtime.
metadata:
  author: codex-research
  version: "17.1.0"
  status: runtime-candidate
---

# Discovery

Turn material uncertainty into the smallest honest artifact that supports the next safe action. Do not turn every request into an interview.

## 0. Triage before loading Discovery

Classify the request with `schemas/request-profile.schema.json` or run:

```bash
discovery triage --profile @request-profile.json --json
```

- `direct`: complete the clear, tiny, low-risk, reversible request without creating Discovery state.
- `confirm_once`: ask one material confirmation with a recommended default, then proceed.
- `discover`: open the adaptive loop because material uncertainty or risk exists.

Explicit discovery requests always enter Discovery. Complexity must earn its cost.

## Core contract

1. Classify **Intent** (`discover|refine|validate`), **Track** (`build|opportunity|change`), and **Depth** (`quick|standard|deep`).
2. Inspect facts; ask decisions. Test uncertainty, prototype preferences, and default only low-risk reversible details.
3. Resolve one decision theme per turn. Meaningful choices include a recommendation, rationale, alternatives, and reversal conditions.
4. Keep facts, artifact claims, findings, assumptions, unknowns, decisions, and authority distinct.
5. Never apply Opportunity demand gates to an authorized Build. Never treat old documentation as current truth without corroboration.
6. Stop when high-impact hard-to-reverse decisions are resolved, tested, or explicitly deferred and the next artifact is honest.
7. Do not expose private reasoning. Show concise decisions, evidence, uncertainty, and requested actions.

## Preferred runtime

When the `discovery` CLI is available, route with the actual capability and model profile:

```bash
discovery route \
  --intent <intent> --track <track> --depth <depth> \
  --capabilities filesystem,code_search,command_execution,persistence \
  --model-tier light \
  --workspace --json
```

Omit unavailable capabilities. Use `--capabilities none` for chat-only environments. Add only applicable flags: `--persistence`, `--extensions`, `--visual`, `--research`, or `--risks ...`.

The host selects a bounded policy bundle, rejects unavailable actions, enforces state transitions, validates structured actions, records one-time capability fallbacks, and commits state through events. Do not directly rewrite `.discovery/state.yaml` when the host is available.

Return node decisions using `schemas/llm-action.schema.json`:

```bash
discovery validate-action --model-tier light --action @action.json
discovery apply-action --workspace . --action @action.json
```

## Capability fallback

Negotiate capabilities once. When a required capability is missing, explain it once and offer at most three paths: upload the artifact, paste the smallest relevant section, or continue under explicit assumptions. Do not repeat the same request after rejection.

## Portable fallback

If the host is unavailable:

1. Read `routes.yaml` and the selected intent, track, validator, and depth bundles only.
2. Load `policies/quick-exit.md` before opening an interview.
3. Load `policies/capability-negotiation.md` when tools are missing.
4. Load `policies/small-model-contract.md` for compact or weaker models.
5. Respect the context budget and defer nonessential files.
6. Use `runtime/state-machine.md` as advisory guidance and disclose that enforcement is not deterministic.

Never load every policy by default.

## Adaptive loop

1. Update evidence and unresolved decisions.
2. Decide whether the next item is inspectable, testable, researchable, prototypeable, safely defaultable, or requires user authority.
3. Choose the cheapest reliable allowed action.
4. Ask at most five accepted high-value questions per pass; light models ask one visible question per response.
5. Load a domain pack or auditor only for a live concern.
6. Give a concise checkpoint every 3–5 turns or after a major conflict.
7. Validate the relevant artifact before handoff. Preserve every unknown with a default, owner, experiment, or revisit condition.

## Completion gate

The stage is complete only when the next goal and owner are clear, no blocking high-impact decision remains, P0 implementation behavior has executable acceptance criteria, current truth and proposed change remain separate, and residual unknowns are explicitly managed.

## Prohibited

- Interviewing a clear, tiny, low-risk, reversible request.
- Asking for facts available in files, code, tests, data, or tools.
- Repeating the same capability request after the user declines.
- Loading all policies “just in case.”
- Directly editing deterministic state instead of submitting events.
- Silently redesigning during Validate intent.
- Inventing certainty to pass a gate.
- Treating static protocol coverage as live-model superiority.
