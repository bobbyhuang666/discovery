#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--workspace',required=True); ap.add_argument('--project-id',required=True); ap.add_argument('--domains',required=True,help='comma-separated domain seed names'); ap.add_argument('--force',action='store_true'); args=ap.parse_args()
    target=Path(args.workspace).resolve()/'.discovery/project-ontology.yaml'
    if target.exists() and not args.force: raise SystemExit(f'{target} exists; use --force')
    domains=[x.strip() for x in args.domains.split(',') if x.strip()]; aspects=[]; generated=[]; seen=set()
    for domain in domains:
        path=ROOT/'ontology/seeds'/f'{domain}.yaml'
        if not path.is_file(): raise SystemExit(f'unknown ontology seed: {domain}')
        seed=yaml.safe_load(path.read_text(encoding='utf-8')); generated.append(str(path.relative_to(ROOT)))
        for aspect in seed['aspects']:
            if aspect['id'] in seen: continue
            seen.add(aspect['id'])
            converted={'id':aspect['id'],'name':aspect['name'],'dimensions':[]}
            for dim in aspect['dimensions']:
                converted['dimensions'].append({'id':dim['id'],'name':dim['name'],'slots':[{'id':s['id'],'name':s['name'],'status':'untouched','evidence_refs':[],'decision_refs':[],'requirement_refs':[],'rationale':''} for s in dim['slots']]})
            aspects.append(converted)
    data={'schema_version':'1.0','project_id':args.project_id,'generated_from':generated,'aspects':aspects,'updated_at':dt.datetime.now(dt.timezone.utc).isoformat()}
    schema=json.loads((ROOT/'schemas/project-ontology.schema.json').read_text(encoding='utf-8')); Draft202012Validator(schema,format_checker=FormatChecker()).validate(data)
    target.parent.mkdir(parents=True,exist_ok=True); tmp=target.with_suffix('.yaml.tmp'); tmp.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8'); tmp.replace(target); print(target); return 0
if __name__=='__main__': raise SystemExit(main())
