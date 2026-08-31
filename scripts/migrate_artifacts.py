#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,shutil
from pathlib import Path
import yaml

def migrate_state(path:Path)->bool:
    d=yaml.safe_load(path.read_text(encoding='utf-8')); version=str(d.get('schema_version',''))
    if version=='4.1': return False
    if version not in {'2.0','3.0','4.0'}: raise SystemExit(f'Unsupported state schema: {version}')
    if version=='2.0':
        d.setdefault('clarification_pass',{'max_questions':5,'asked':0,'accepted':0,'active_concern_id':None,'remaining_high_impact':[]})
        d.setdefault('coverage_map',{'ref':'.discovery/coverage-map.yaml','clear':0,'partial':0,'missing':0,'not_applicable':0,'deferred':0})
        d.setdefault('constitution',{'ref':None,'status':'missing'})
        d.setdefault('approval',{'level':'none','status':'not_required','approver':None,'artifact_ref':None})
        d.setdefault('artifact_graph',{'available_actions':['inspect'],'blocked_actions':[]})
    d['schema_version']='4.1'; d['skill_version']='17.1.0'
    runtime=d.setdefault('runtime',{'mode':'deterministic-host','revision':0,'loaded_bundles':[],'context_metrics':{'budget_chars':0,'used_chars':0,'loaded_files':[],'deferred_files':[]},'last_committed_at':None})
    runtime.setdefault('model_tier','standard')
    runtime.setdefault('capabilities',['filesystem','command_execution','persistence'])
    runtime.setdefault('capability_notices',[])
    d.setdefault('last_event_id',None)
    d.setdefault('clarification_pass',{'max_questions':5,'asked':0,'accepted':0,'active_concern_id':None,'remaining_high_impact':[]})
    d.setdefault('coverage_map',{'ref':'.discovery/coverage-map.yaml','clear':0,'partial':0,'missing':0,'not_applicable':0,'deferred':0})
    d.setdefault('constitution',{'ref':None,'status':'missing'})
    d.setdefault('approval',{'level':'none','status':'not_required','approver':None,'artifact_ref':None})
    d.setdefault('artifact_graph',{'available_actions':['inspect'],'blocked_actions':[]})
    d['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat(); write_backup(path,d); return True

def migrate_spec(path:Path)->bool:
    d=yaml.safe_load(path.read_text(encoding='utf-8')); version=str(d.get('schema_version',''))
    if version=='2.0': return False
    if version!='1.0': raise SystemExit(f'Unsupported living-spec schema: {version}')
    d['schema_version']='2.0'; d.setdefault('constitution_ref',None); d['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat(); write_backup(path,d); return True

def write_backup(path:Path,data:dict)->None:
    backup=path.with_suffix(path.suffix+'.bak'); shutil.copy2(path,backup); tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8'); tmp.replace(path)

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--workspace',required=True); args=ap.parse_args(); base=Path(args.workspace).resolve()/'.discovery'; changed=[]
    state=base/'state.yaml'; spec=base/'specs/current.yaml'
    if state.is_file() and migrate_state(state): changed.append(str(state))
    if spec.is_file() and migrate_spec(spec): changed.append(str(spec))
    print(f'Migrated: {len(changed)}'); [print(x) for x in changed]; return 0
if __name__=='__main__': raise SystemExit(main())
