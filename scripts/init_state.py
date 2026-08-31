#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, subprocess, uuid, sys
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from discovery_runtime.io import atomic_write_yaml

def git_value(cwd:Path,args:list[str]):
    p=subprocess.run(['git',*args],cwd=cwd,text=True,capture_output=True)
    return p.stdout.strip() or None if p.returncode==0 else None

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--workspace',required=True); ap.add_argument('--project-id',required=True); ap.add_argument('--intent',choices=['discover','refine','validate'],default='discover'); ap.add_argument('--track',choices=['build','opportunity','change'],default='build'); ap.add_argument('--depth',choices=['quick','standard','deep'],default='standard'); ap.add_argument('--model-tier',choices=['light','standard','strong'],default='standard'); ap.add_argument('--capabilities',default='filesystem,command_execution,persistence'); ap.add_argument('--force',action='store_true'); args=ap.parse_args()
    workspace=Path(args.workspace).resolve(); target=workspace/'.discovery'; state_path=target/'state.yaml'
    if state_path.exists() and not args.force: raise SystemExit(f'{state_path} exists; use --force to replace')
    target.mkdir(parents=True,exist_ok=True); (target/'.gitignore').write_text('*\n!.gitignore\n',encoding='utf-8')
    now=dt.datetime.now(dt.timezone.utc).isoformat(); state=yaml.safe_load((ROOT/'templates/state.yaml').read_text(encoding='utf-8'))
    state.update({'session_id':str(uuid.uuid4()),'intent':args.intent,'track':args.track,'depth':args.depth,'updated_at':now})
    state['project_fingerprint'].update({'project_id':args.project_id,'branch':git_value(workspace,['branch','--show-current']),'revision':git_value(workspace,['rev-parse','HEAD'])})
    state['runtime']['model_tier']=args.model_tier
    state['runtime']['capabilities']=[x.strip() for x in args.capabilities.split(',') if x.strip() and x.strip().lower()!='none']
    state['runtime']['capability_notices']=[]
    schema=json.loads((ROOT/'schemas/state.schema.json').read_text(encoding='utf-8')); Draft202012Validator(schema,format_checker=FormatChecker()).validate(state)
    atomic_write_yaml(state_path,state)
    (target/'events.jsonl').write_text('',encoding='utf-8'); (target/'decisions.md').write_text((ROOT/'templates/decisions.md').read_text(encoding='utf-8'),encoding='utf-8'); (target/'context-index.yaml').write_text("schema_version: '1.0'\nartifacts: []\n",encoding='utf-8')
    coverage=yaml.safe_load((ROOT/'templates/coverage-map.yaml').read_text(encoding='utf-8')); coverage['session_id']=state['session_id']; coverage['updated_at']=now
    (target/'coverage-map.yaml').write_text(yaml.safe_dump(coverage,sort_keys=False,allow_unicode=True),encoding='utf-8')
    handoff={'schema_version':'1.0','session_id':state['session_id'],'intent':args.intent,'track':args.track,'depth':args.depth,'stage':'orienting','current_decision_id':None,'next_recommended_action':state['next_action'],'in_progress_work':[],'blockers':[],'pending_human_actions':[],'files_to_read_next':[],'living_spec_ref':None,'active_change_refs':[],'state_version':'4.1','project_fingerprint':state['project_fingerprint'],'updated_at':now}
    (target/'handoff.json').write_text(json.dumps(handoff,indent=2),encoding='utf-8'); print(state_path); return 0
if __name__=='__main__': raise SystemExit(main())
