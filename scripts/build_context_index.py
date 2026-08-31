#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime as dt,hashlib,os
from pathlib import Path
import yaml
IGNORE={'.git','.discovery','node_modules','.venv','venv','dist','build','target','__pycache__'}
MANIFESTS={'package.json','pyproject.toml','requirements.txt','Cargo.toml','go.mod','pom.xml','build.gradle','docker-compose.yml','Dockerfile'}
def classify(path:Path)->str:
    name=path.name.lower(); parts={p.lower() for p in path.parts}
    if path.name in MANIFESTS:return 'manifest'
    if 'test' in parts or 'tests' in parts or name.startswith('test_') or name.endswith(('_test.py','.spec.ts','.test.ts')):return 'test'
    if path.suffix.lower() in {'.md','.rst','.txt'}:return 'documentation'
    if path.suffix.lower() in {'.yaml','.yml','.json','.toml','.ini','.env'}:return 'configuration'
    if path.suffix.lower() in {'.py','.js','.ts','.tsx','.jsx','.go','.rs','.java','.kt','.rb','.php','.cs','.cpp','.c','.h'}:return 'source'
    return 'other'
def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--workspace',required=True); ap.add_argument('--max-files',type=int,default=5000); args=ap.parse_args()
    ws=Path(args.workspace).resolve(); items=[]
    for root,dirs,files in os.walk(ws):
        dirs[:]=[d for d in dirs if d not in IGNORE]
        for fn in files:
            p=Path(root)/fn
            try: rel=p.relative_to(ws); stat=p.stat()
            except OSError: continue
            items.append({'path':str(rel),'kind':classify(rel),'size':stat.st_size,'mtime_ns':stat.st_mtime_ns})
            if len(items)>=args.max_files: break
        if len(items)>=args.max_files: break
    digest=hashlib.sha256('\n'.join(f"{i['path']}:{i['size']}:{i['mtime_ns']}" for i in items).encode()).hexdigest()
    data={'schema_version':'1.0','workspace':str(ws),'generated_at':dt.datetime.now(dt.timezone.utc).isoformat(),'fingerprint':digest,'truncated':len(items)>=args.max_files,'artifacts':items}
    target=ws/'.discovery'; target.mkdir(parents=True,exist_ok=True); path=target/'context-index.yaml'; path.write_text(yaml.safe_dump(data,sort_keys=False,allow_unicode=True),encoding='utf-8'); print(path); return 0
if __name__=='__main__': raise SystemExit(main())
