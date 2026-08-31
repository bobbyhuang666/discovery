#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from discovery_runtime.state_machine import validate_invariants

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('path',nargs='?',default='.discovery/state.yaml'); args=ap.parse_args(); path=Path(args.path)
    data=yaml.safe_load(path.read_text(encoding='utf-8')); schema=json.loads((ROOT/'schemas/state.schema.json').read_text(encoding='utf-8'))
    errors=[f"schema at {list(i.path)}: {i.message}" for i in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(data)]
    errors += [f"invariant: {x}" for x in validate_invariants(data)]
    if errors:
        for e in errors: print('ERROR:',e)
        return 1
    print(f'Valid state and invariants: {path}'); return 0
if __name__=='__main__': raise SystemExit(main())
