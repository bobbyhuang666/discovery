#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, re, uuid, json
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]

def slug(s:str)->str:
    x=re.sub(r'[^A-Za-z0-9]+','-',s).strip('-').upper()
    return x[:40] or 'CHANGE'

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--workspace',required=True); ap.add_argument('--title',required=True); ap.add_argument('--intent',choices=['discover','refine','validate'],default='discover')
    args=ap.parse_args(); ws=Path(args.workspace).resolve(); base=ws/'.discovery/changes'; base.mkdir(parents=True,exist_ok=True)
    now=dt.datetime.now(dt.timezone.utc); cid=f"CHG-{now:%Y%m%d}-{slug(args.title)}-{uuid.uuid4().hex[:6].upper()}"; folder=base/cid; folder.mkdir()
    data=yaml.safe_load((ROOT/'templates/change-proposal.yaml').read_text(encoding='utf-8'))
    data.update({'change_id':cid,'title':args.title,'intent':args.intent,'created_at':now.isoformat(),'updated_at':now.isoformat()})
    schema=json.loads((ROOT/'schemas/change-proposal.schema.json').read_text(encoding='utf-8')); Draft202012Validator(schema,format_checker=FormatChecker()).validate(data)
    (folder/'proposal.yaml').write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8')
    for name,content in [('impact.yaml',{'schema_version':'1.0','change_id':cid,'notes':[]}),('verification.yaml',{'schema_version':'1.0','change_id':cid,'evidence':[]})]:
        (folder/name).write_text(yaml.safe_dump(content,sort_keys=False),encoding='utf-8')
    print(folder); return 0
if __name__=='__main__': raise SystemExit(main())
