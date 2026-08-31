#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, shutil
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
import json
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--workspace', required=True)
    ap.add_argument('--project-id', required=True)
    ap.add_argument('--force', action='store_true')
    args=ap.parse_args()
    ws=Path(args.workspace).resolve(); base=ws/'.discovery'
    current=base/'specs/current.yaml'
    if current.exists() and not args.force:
        raise SystemExit(f'{current} exists; use --force to replace')
    (base/'specs').mkdir(parents=True,exist_ok=True); (base/'changes').mkdir(exist_ok=True); (base/'archive').mkdir(exist_ok=True)
    data=yaml.safe_load((ROOT/'templates/living-spec.yaml').read_text(encoding='utf-8'))
    data['project_id']=args.project_id; data['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    constitution=base/'constitution.yaml'
    data['constitution_ref']=str(constitution.relative_to(ws)) if constitution.exists() else None
    schema=json.loads((ROOT/'schemas/living-spec.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator(schema,format_checker=FormatChecker()).validate(data)
    tmp=current.with_suffix('.yaml.tmp'); tmp.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8'); tmp.replace(current)
    print(current); return 0
if __name__=='__main__': raise SystemExit(main())
