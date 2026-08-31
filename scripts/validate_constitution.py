#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator,FormatChecker
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('path',nargs='?',default='.discovery/constitution.yaml'); args=ap.parse_args()
    path=Path(args.path); data=yaml.safe_load(path.read_text(encoding='utf-8')); schema=json.loads((ROOT/'schemas/constitution.schema.json').read_text(encoding='utf-8'))
    errors=list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(data))
    if errors:
        for e in errors: print(f'ERROR at {list(e.path)}: {e.message}')
        return 1
    print(f'Valid constitution: {path}'); return 0
if __name__=='__main__': raise SystemExit(main())
