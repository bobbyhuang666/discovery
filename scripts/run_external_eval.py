#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,shlex,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main()->int:
    ap=argparse.ArgumentParser(description='Run or export a model-agnostic Discovery evaluation')
    ap.add_argument('--command',default=''); ap.add_argument('--scenario',required=True); ap.add_argument('--runs-dir',required=True); ap.add_argument('--dry-run',action='store_true'); args=ap.parse_args()
    corpus=json.loads((ROOT/'evals/interview-scenarios.json').read_text(encoding='utf-8'))
    scenarios=corpus.get('scenarios',corpus) if isinstance(corpus,dict) else corpus
    scenario=next((s for s in scenarios if s.get('id')==args.scenario),None)
    if scenario is None: raise SystemExit(f'Unknown scenario: {args.scenario}')
    runs=Path(args.runs_dir).resolve(); runs.mkdir(parents=True,exist_ok=True)
    input_path=runs/f'{args.scenario}-input.json'; output_path=runs/f'{args.scenario}-run.json'
    packet={'schema_version':'1.0','skill_path':str(ROOT/'SKILL.md'),'scenario':scenario,'instructions':'Run the conversation using the target skill. Write an annotated eval run matching schemas/eval-run.schema.json.'}
    input_path.write_text(json.dumps(packet,indent=2,ensure_ascii=False),encoding='utf-8')
    if args.dry_run:
        print(input_path); return 0
    if not args.command: raise SystemExit('--command is required unless --dry-run')
    command=args.command.format(input=shlex.quote(str(input_path)),output=shlex.quote(str(output_path)))
    p=subprocess.run(command,shell=True)
    if p.returncode: return p.returncode
    if not output_path.is_file(): raise SystemExit(f'External runner did not create {output_path}')
    print(output_path); return 0
if __name__=='__main__': raise SystemExit(main())
