#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(script):
    p=subprocess.run(['python',str(ROOT/'scripts'/script)],cwd=ROOT,text=True,capture_output=True);return p.returncode,(p.stdout+p.stderr).strip()
def main():
    checks=[('Runtime unit tests','__UNIT__'),('Structural/schema/smoke','validate_skill.py'),('Routing regression','run_evals.py'),('Interview corpus','validate_eval_corpus.py'),('Static protocol coverage audit','run_protocol_audit.py')];results=[]
    for label,s in checks:
        if s=='__UNIT__':
            p=subprocess.run(['python','-m','unittest','discover','-s','tests','-v'],cwd=ROOT,text=True,capture_output=True,env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'src')}); results.append((label,p.returncode,(p.stdout+p.stderr).strip()))
        else: results.append((label,*run(s)))
    md=list(ROOT.rglob('*.md'));status='PASS' if all(c==0 for _,c,_ in results) else 'FAIL';now=dt.datetime.now(dt.timezone.utc).isoformat();sections='\n\n'.join(f"## {l}\n\n```text\n{o}\n```" for l,c,o in results)
    report=f"""# Verification Report\n\nGenerated automatically. Do not edit by hand.\n\n- **Status:** {status}\n- **Generated at:** {now}\n- **Markdown files:** {len(md)}\n- **Total Markdown lines:** {sum(len(p.read_text(encoding='utf-8').splitlines()) for p in md)}\n- **SKILL.md lines:** {len((ROOT/'SKILL.md').read_text(encoding='utf-8').splitlines())}\n- **Automated checks:** {len(results)}\n\n{sections}\n"""
    (ROOT/'VERIFICATION.md').write_text(report,encoding='utf-8');print(f'Generated VERIFICATION.md with status {status}');return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
