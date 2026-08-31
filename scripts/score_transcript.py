#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from jsonschema import Draft202012Validator
ROOT=Path(__file__).resolve().parents[1]

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--run',required=True); args=ap.parse_args(); run=json.loads(Path(args.run).read_text(encoding='utf-8')); schema=json.loads((ROOT/'schemas/eval-run.schema.json').read_text(encoding='utf-8')); errors=list(Draft202012Validator(schema).iter_errors(run))
    if errors:
        [print('ERROR:',list(e.path),e.message) for e in errors]; return 1
    scenarios={s['id']:s for s in json.loads((ROOT/'evals/interview-scenarios.json').read_text(encoding='utf-8'))}; s=scenarios.get(run['scenario_id'])
    if not s: print('unknown scenario'); return 1
    hidden={x['id'] for x in s['hidden_requirements']}; critical={x['id'] for x in s['hidden_requirements'] if x['critical']}; discovered=set(run['final']['discovered_requirement_ids']); resolved=set(run['final']['resolved_decision_ids']); fact_ids={x['id'] for x in s['discoverable_facts']}
    assistant=[t for t in run['turns'] if t['role']=='assistant']; user=[t for t in run['turns'] if t['role']=='user']
    asked_facts=sum(len(set(t.get('questioned_fact_ids',[])) & fact_ids) for t in assistant); repeats=sum(1 for t in assistant if t.get('repeated_question')); unsupported=sum(t.get('unsupported_claim_count',0) for t in assistant); user_words=sum(len(t['content'].split()) for t in user)
    first_critical=None
    for i,t in enumerate(assistant,1):
        if set(t.get('discovered_requirement_ids',[])) & critical: first_critical=i; break
    metrics={
      'hidden_requirement_recall': len(discovered&hidden)/len(hidden) if hidden else 1,
      'critical_requirement_recall': len(discovered&critical)/len(critical) if critical else 1,
      'critical_decision_resolution': len(resolved&set(s['critical_decisions']))/len(s['critical_decisions']) if s['critical_decisions'] else 1,
      'environment_fact_questions': asked_facts,
      'repeated_questions': repeats,
      'unsupported_claims': unsupported,
      'user_word_burden': user_words,
      'first_critical_discovery_turn': first_critical
    }
    print(json.dumps(metrics,indent=2)); return 0
if __name__=='__main__': sys.exit(main())
