#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    schema=json.loads((ROOT/'schemas/interview-scenario.schema.json').read_text(encoding='utf-8')); data=json.loads((ROOT/'evals/interview-scenarios.json').read_text(encoding='utf-8')); errors=list(Draft202012Validator(schema).iter_errors(data)); ids=[x.get('id') for x in data]
    if len(ids)!=len(set(ids)): print('duplicate scenario ids'); return 1
    print(f'Interview scenarios: {len(data)}'); print(f'Schema errors: {len(errors)}'); [print('  ERROR:',list(e.path),e.message) for e in errors]; return 1 if errors else 0
if __name__=='__main__': sys.exit(main())
