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

## Optional: deliver a working local product

Use delivery only when the user explicitly wants a working website, app, or internal tool. Analysis-only, exploration, and specification requests stay in the Discovery loop. Delivery is a separate outcome: `Discovery complete` does not mean `Product delivered`.

```bash
discovery deliver "A small tool for tracking team equipment" \
  --workspace ./equipment-tool \
  --brief ./equipment-brief.md \
  --max-attempts 3

discovery delivery-status --workspace ./equipment-tool
discovery delivery-resume --workspace ./equipment-tool --feedback "Add a filter by owner"
discovery delivery-resume --workspace ./equipment-tool --replan-reason "The check assumes an unavailable fixture path"
discovery delivery-preview --workspace ./equipment-tool
```

`deliver` uses the locally configured Codex model unless `--model` or `--reasoning-effort` explicitly overrides it. `--executor codex` is the default; `--codex-bin` selects that CLI executable. In an app environment that dispatches subagents, select `--executor handoff` to preserve the requested `--model` and `--reasoning-effort` without invoking the standalone Codex CLI. `--executor-timeout` sets the wait limit in seconds. Delivery state is saved in `<workspace>/.delivery/state.yaml`; the product is under `<workspace>/product`. The loop runs bounded plan/build/run/acceptance/review/repair work and may ask for input when a material choice blocks progress. No command publishes or deploys the product.

```bash
discovery deliver "A small tool for tracking team equipment" \
  --workspace ./equipment-tool \
  --executor handoff --model gpt-6-luna --reasoning-effort max
```

With `--executor handoff`, the CLI prints a unique `request.json` path to stderr and waits for the host. The host should dispatch a fresh subagent using the requested model and effort in that request, have it execute the prompt within the supplied product scope, then atomically write a schema-conforming JSON object to the request's `response_path` (write a temporary file in that directory and rename it). Request files contain the prompt, phase, workspace, schema, model, effort, unique response path, and status. The handoff adapter itself does not call the subagent service or change the requested model. Timeout or Ctrl-C is recorded in the request status.

`delivery-preview` runs the local product in the foreground, prints its loopback URL, and stops it on Ctrl-C. Its port is saved per launch hostname in `.delivery/state.yaml`, so reopening the same preview origin in the same browser profile can reuse client-side storage. If that saved port is occupied, preview fails instead of silently changing origins. Changing the plan's hostname creates a separate browser origin and does not migrate its client-side data; the runtime warns when origins differ. Acceptance-check origins may vary by check, so verify browser-local persistence at the same origin within one check. The URL recorded from acceptance checks is not a live server.

The delivery runtime currently supports macOS and Linux. Launch and acceptance checks run as local child processes, not in a security sandbox. The Codex adapter uses Codex CLI sandbox options for agent calls; the handoff host is responsible for permissions when it dispatches an agent. In either mode, review the plan's commands and use a trusted workspace.

Delivery commands work outside the Discovery skill directory. They accept `--json` to print a structured result; for JSON preview mode, the live URL goes to stderr and the final result goes to stdout. For `deliver`, `delivery-status`, and `delivery-resume`, exit codes are `0` delivered, `2` needs input, `3` blocked, budget exhausted, or interrupted, and `1` for a command error. Preview returns its local process exit code (`0` on a normal stop).

Delivered outcome entrypoints use a shell-safe argv for this host's Python interpreter and installed Skill `src`, requiring neither a global `discovery` command nor `PYTHONPATH`; CLI output adapts the exact legacy command format without rewriting saved records.

## Install Discovery into a skills directory

`python3 scripts/install_skill.py --platform codex` installs locally under `.codex/skills/discovery`; use `claude` or `agents` for those clients. Local installs can target another project with `--project-root ./my-project`; `--scope global` selects the current user's corresponding skills directory. Existing installs are left untouched unless `--force` is given, and replacement is staged before the exact target is swapped. Source and destination symlinks are rejected. A default local install from the Discovery source directory is supported without copying the installer output back into itself.

The installer copies the Skill; it does not install Python dependencies or a global `discovery` command. With Python 3.11+ and the dependencies from `requirements.lock` already available, the optional runtime can also be run without a global installation: `PYTHONPATH=/absolute/path/to/discovery/src python3 -B -m discovery_runtime.cli --help`. Replace that path with the extracted or installed Skill directory; the same prefix works with the commands above. `-B` prevents imports from writing bytecode into the Skill installation; keep generated state and products in the chosen workspace.

## Build a verified Skill ZIP

From the skill repository, run `python3 scripts/package_skill.py`; use `--output /path/to/new.zip` for a candidate path. Packaging first copies the source into an isolated `discovery/` tree, generates `VERIFICATION.md` there, then cold-unpacks and tests the ZIP before publishing. It excludes repository metadata, caches, virtual environments, build outputs, egg-info, bytecode, and OS metadata while retaining other hidden files. It also omits only known root-relative generated outputs: top-level `.discovery`, `.delivery`, and `.delivery-data` state, plus project-local `.codex/skills`, `.claude/skills`, and `.agents/skills` install trees. This is generated-output cleanup, not a general secret sanitizer. Source symlinks are rejected rather than followed. Existing outputs are never replaced by default; `--force` replaces only the exact `--output` file and only after every check passes.
