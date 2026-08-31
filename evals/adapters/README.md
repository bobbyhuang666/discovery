# External Evaluation Adapters

`run_external_eval.py` allows the included scenarios to be executed by any agent runtime that can accept an input JSON file and write an evaluation-run JSON file.

The benchmark does not ship credentials or call paid APIs by default.

Example:

```bash
python scripts/run_external_eval.py \
  --command 'my-agent --input {input} --output {output}' \
  --scenario build-quick-internal-automation \
  --runs-dir /tmp/discovery-runs
```

The external command must produce a file compatible with `schemas/eval-run.schema.json`. Use `--dry-run` to export prompt packets without executing a model.
