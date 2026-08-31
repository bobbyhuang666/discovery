# Usage

## Step 1: Triage

Before loading Discovery, classify the request:

- `direct`: clear, tiny, low-risk, reversible; complete it immediately;
- `confirm_once`: one material ambiguity; recommend a default and ask once;
- `discover`: material uncertainty or risk; enter the full loop.

```bash
discovery triage --profile @templates/request-profile.json --json
```

## Step 2: Route only relevant policies

Discovery then selects:

- Intent: Discover, Refine, Validate
- Track: Build, Opportunity, Change
- Depth: Quick, Standard, Deep
- Model tier: Light, Standard, Strong
- Actual runtime capabilities

```bash
discovery route \
  --intent discover --track build --depth quick \
  --model-tier light --capabilities none --json
```

A chat-only route loads capability fallback guidance instead of workspace inspection.

## Step 3: Use structured actions

For light models, use one visible question, at most three options, three requested files, and three state events per action.

For durable work, initialize `.discovery` with `scripts/init_state.py` and use the Host to apply events and actions.
