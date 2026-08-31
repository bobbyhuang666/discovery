#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]

def issues(path:Path,schema_path:Path):
    data=yaml.safe_load(path.read_text(encoding='utf-8')); schema=json.loads(schema_path.read_text(encoding='utf-8'))
    return [f"{path}: {list(e.path)} {e.message}" for e in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(data)]

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--workspace',required=True); args=ap.parse_args(); base=Path(args.workspace).resolve()/'.discovery'; errors=[]
    current=base/'specs/current.yaml'
    if not current.is_file(): errors.append(f'missing {current}')
    else: errors+=issues(current,ROOT/'schemas/living-spec.schema.json')
    for p in (base/'changes').glob('*/proposal.yaml') if (base/'changes').exists() else []: errors+=issues(p,ROOT/'schemas/change-proposal.schema.json')
    for p in (base/'archive').glob('*/proposal.yaml') if (base/'archive').exists() else []: errors+=issues(p,ROOT/'schemas/change-proposal.schema.json')
    print(f'Living-spec errors: {len(errors)}'); [print('  ERROR:',e) for e in errors]; return 1 if errors else 0
if __name__=='__main__': raise SystemExit(main())
