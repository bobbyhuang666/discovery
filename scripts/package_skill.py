#!/usr/bin/env python3
from __future__ import annotations
import os, shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT.parent/'discovery-v17.1.zip'
env={**os.environ,'PYTHONPATH':str(ROOT/'src'),'DISCOVERY_SKILL_ROOT':str(ROOT)}
subprocess.run([sys.executable,str(ROOT/'scripts/generate_verification.py')],check=True,cwd=ROOT,env=env)
for cache in ROOT.rglob('__pycache__'): shutil.rmtree(cache)
for p in ROOT.rglob('*.pyc'): p.unlink()
for generated in [ROOT/'build', ROOT/'src/discovery_runtime.egg-info']:
    if generated.exists(): shutil.rmtree(generated)
if OUT.exists(): OUT.unlink()
shutil.make_archive(str(OUT.with_suffix('')),'zip',root_dir=ROOT.parent,base_dir=ROOT.name)
with tempfile.TemporaryDirectory() as td:
    shutil.unpack_archive(str(OUT),td); cold=Path(td)/ROOT.name
    cold_env={**env,'PYTHONPATH':str(cold/'src'),'DISCOVERY_SKILL_ROOT':str(cold),'DISCOVERY_FAST_VALIDATE':'1'}
    subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],check=True,cwd=cold,env=cold_env)
    subprocess.run([sys.executable,str(cold/'scripts/validate_skill.py')],check=True,cwd=cold,env=cold_env)
print(OUT)
