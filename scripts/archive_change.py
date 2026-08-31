#!/usr/bin/env python3
from __future__ import annotations
import argparse, shutil
from pathlib import Path
import yaml

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--workspace',required=True); ap.add_argument('--change-id',required=True); args=ap.parse_args()
    base=Path(args.workspace).resolve()/'.discovery'; src=base/'changes'/args.change_id; dst=base/'archive'/args.change_id; proposal=src/'proposal.yaml'; current=base/'specs/current.yaml'
    if not proposal.is_file() or not current.is_file(): raise SystemExit('missing proposal or current living spec')
    pdata=yaml.safe_load(proposal.read_text(encoding='utf-8')); cdata=yaml.safe_load(current.read_text(encoding='utf-8'))
    if pdata.get('status')!='verified': raise SystemExit('change must be verified before archive')
    if args.change_id not in cdata.get('applied_changes',[]): raise SystemExit('current spec must record the applied change before archive')
    dst.parent.mkdir(parents=True,exist_ok=True)
    if dst.exists(): raise SystemExit(f'{dst} already exists')
    pdata['status']='archived'; proposal.write_text(yaml.safe_dump(pdata,sort_keys=False,allow_unicode=True),encoding='utf-8'); shutil.move(str(src),str(dst)); print(dst); return 0
if __name__=='__main__': raise SystemExit(main())
