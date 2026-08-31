#!/usr/bin/env python3
from __future__ import annotations
import argparse,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PLATFORMS={
    'codex':('.codex/skills','~/.codex/skills'),
    'claude':('.claude/skills','~/.claude/skills'),
    'agents':('.agents/skills','~/.agents/skills'),
}
def ignore(_dir,names):
    return {n for n in names if n in {'__pycache__','.git','.DS_Store'} or n.endswith('.pyc') or n.endswith('.zip')}
def main()->int:
    ap=argparse.ArgumentParser(description='Install Discovery into a supported skills directory')
    ap.add_argument('--platform',choices=sorted(PLATFORMS),required=True); ap.add_argument('--scope',choices=['local','global'],default='local'); ap.add_argument('--project-root',default='.'); ap.add_argument('--force',action='store_true'); args=ap.parse_args()
    local,global_=PLATFORMS[args.platform]
    base=(Path(args.project_root).resolve()/local) if args.scope=='local' else Path(global_).expanduser()
    dest=base/'discovery'; base.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        if not args.force: raise SystemExit(f'{dest} exists; use --force to replace')
        if dest.resolve()==ROOT.resolve(): raise SystemExit('Refusing to replace the source directory')
        shutil.rmtree(dest)
    shutil.copytree(ROOT,dest,ignore=ignore)
    print(dest); return 0
if __name__=='__main__': raise SystemExit(main())
