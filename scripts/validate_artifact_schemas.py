#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('path',nargs='?',default=str(ROOT/'templates/artifact-schemas.yaml')); args=ap.parse_args()
    path=Path(args.path); data=yaml.safe_load(path.read_text(encoding='utf-8')); schema=json.loads((ROOT/'schemas/artifact-schemas.schema.json').read_text(encoding='utf-8'))
    errors=list(Draft202012Validator(schema).iter_errors(data))
    for artifact in data.get('artifacts',[]):
        schema_path=ROOT/artifact['schema_path']
        if artifact.get('enabled') and not schema_path.is_file(): errors.append(f"missing registered schema: {artifact['schema_path']}")
    if errors:
        for e in errors: print(f'ERROR: {e.message if hasattr(e,"message") else e}')
        return 1
    print(f'Valid artifact schema registry: {path}'); return 0
if __name__=='__main__': raise SystemExit(main())
