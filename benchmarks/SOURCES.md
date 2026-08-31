# Competitor Source Register

Reviewed on 2026-07-27. The protocol coverage audit credits only behavior explicitly stated in the listed source artifacts. Repository popularity is not part of the score.

| System | Repository | Reviewed source | Source identity captured during review | Main capability used in comparison |
|---|---|---|---|---|
| Superpowers Brainstorming | `obra/superpowers` | **skills/brainstorming/SKILL.md** | blob `789c3a1990b9ab3896c4d8b0b708525ac83fe5ce` | context inspection, alternatives, approval gates, visual companion |
| Matt Pocock Grilling | `mattpocock/skills` | **skills/productivity/grilling/SKILL.md** | blob `52d8eb3cadd2dca62634d5dccfa73ea6b725b117` | decision-tree interviewing, recommended answers, inspect facts |
| GitHub Spec Kit | `github/spec-kit` | **templates/commands/clarify.md** | blob `fb0e91281fe2b58bce709e8a613bf0fcbc0ecf31` | five-question budget, constitution, incremental clarification |
| OpenSpec | `Fission-AI/OpenSpec` | **docs/workflows.md** | blob `82f1e1efa2670c00a89e794e4de27b775833c4b8` | action-oriented living-spec and change lifecycle |
| BMad Method | `bmad-code-org/BMAD-METHOD` | **docs/reference/workflow-map.md** | blob `44733a1796d28e42b26ec6c1a117f02b539245` | create/update/validate intents, lifecycle routing, readiness |
| GSD | `gsd-build/get-shit-done` | **docs/FEATURES.md** | blob `f6a46c6128e85d846fe3348577b5f5c481efae45` | persistent context, research, workstreams, verification and model routing |

## Evidence-coding rules

- `0`: absent from the reviewed source.
- `1`: partially, indirectly, or externally supported.
- `2`: explicitly operationalized by instructions, artifacts, schemas, or executable tooling.
- Scores are source-contract coverage, not observed conversational quality.
- A future release must re-review profiles when the source identity changes.
- Live model evaluation under `evals/` is the decisive empirical layer.
