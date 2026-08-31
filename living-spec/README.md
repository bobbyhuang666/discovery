# Living Specification

The living specification stores current accepted truth separately from proposed changes.

Initialize it with:

```bash
python scripts/init_living_spec.py --workspace /path/to/project --project-id my-project
```

Create a proposal with:

```bash
python scripts/create_change.py --workspace /path/to/project --title "Add team workspaces" --intent discover
```

Validate with:

```bash
python scripts/validate_living_spec.py --workspace /path/to/project
```

Archive only after the current specification records the applied change and the proposal is verified.
