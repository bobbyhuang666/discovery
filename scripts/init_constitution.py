#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    ap=argparse.ArgumentParser(description='Initialize .discovery/constitution.yaml')
    ap.add_argument('--workspace',required=True); ap.add_argument('--project-id',required=True)
    ap.add_argument('--status',choices=['draft','active','not_applicable'],default='draft')
    ap.add_argument('--force',action='store_true'); args=ap.parse_args()
    workspace=Path(args.workspace).resolve(); target=workspace/'.discovery'; target.mkdir(parents=True,exist_ok=True)
    path=target/'constitution.yaml'
    if path.exists() and not args.force: raise SystemExit(f'{path} exists; use --force to replace')
    data=yaml.safe_load((ROOT/'templates/constitution.yaml').read_text(encoding='utf-8'))
    data.update({'project_id':args.project_id,'status':args.status,'updated_at':dt.datetime.now(dt.timezone.utc).isoformat()})
    schema=json.loads((ROOT/'schemas/constitution.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(data)
    tmp=path.with_suffix('.yaml.tmp'); tmp.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8'); tmp.replace(path)
    print(path); return 0
if __name__=='__main__': raise SystemExit(main())
