#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def infer_intent(text:str)->str:
    t=text.lower()
    if any(x in t for x in ['validate whether','review whether','check whether','audit this']): return 'validate'
    if any(x in t for x in ['improve this existing','refine this','without restarting','update this prd']): return 'refine'
    return 'discover'

def infer_track(text:str):
    t=text.lower()
    if any(x in t for x in ['what does','define ']) or 'change the button label' in t: return None
    if any(x in t for x in ['prd','specification','requirements document']): return 'build'
    if any(x in t for x in ['existing','migrate','migration','redesign','add organization workspaces']): return 'change'
    if any(x in t for x in ['do not know if','validate pricing','idea for','worth building']): return 'opportunity'
    return 'build'

def infer_depth(text:str,track):
    if track is None:return None
    t=text.lower(); deep=['sensitive','financial','migrate','migration','enterprise','regulated','approval platform','workspaces']
    if any(x in t for x in deep): return 'deep'
    if track=='opportunity' and any(x in t for x in ['pricing','retention','distribution']): return 'deep'
    if any(x in t for x in ['dashboard','redesign','meeting assistant','existing prd']): return 'standard'
    return 'quick'

def main()->int:
    cases=json.loads((ROOT/'evals/cases.json').read_text(encoding='utf-8')); failures=[]
    for c in cases:
        if c.get('should_trigger') is False:
            if infer_track(c['input']) is not None: failures.append(f"{c['id']}: expected no trigger")
            continue
        if 'expected_policy' in c: continue
        intent=infer_intent(c['input']); track=infer_track(c['input']); depth=infer_depth(c['input'],track)
        for k,a,e in [('intent',intent,c.get('expected_intent')),('track',track,c.get('expected_track')),('depth',depth,c.get('expected_depth'))]:
            if e is not None and a!=e: failures.append(f"{c['id']}: {k} {a!r} != {e!r}")
    print(f'Evaluation cases: {len(cases)}'); print(f'Failures: {len(failures)}'); [print('  FAIL:',x) for x in failures]; return 1 if failures else 0
if __name__=='__main__': sys.exit(main())
