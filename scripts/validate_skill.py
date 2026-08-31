#!/usr/bin/env python3
from __future__ import annotations
import json,re,sys,tempfile,subprocess,os
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator,FormatChecker
ROOT=Path(__file__).resolve().parents[1]; ERRORS=[]; WARNINGS=[]
def error(m):ERRORS.append(m)
def warn(m):WARNINGS.append(m)
def load_frontmatter(path):
    text=path.read_text(encoding='utf-8')
    if not text.startswith('---\n'): error(f'{path.relative_to(ROOT)}: missing YAML frontmatter'); return {}
    try:
        _,fm,_=text.split('---',2); v=yaml.safe_load(fm)
        if not isinstance(v,dict): raise ValueError('frontmatter not mapping')
        return v
    except Exception as e:error(f'{path.relative_to(ROOT)}: invalid frontmatter: {e}');return {}
def check_required_structure():
    required=['SKILL.md','README.md','HOST_RUNTIME.md','USAGE.md','pyproject.toml','requirements.lock','routes.yaml','schemas/llm-action.schema.json','templates/llm-action.json','schemas/request-profile.schema.json','templates/request-profile.json','src/discovery_runtime/triage.py','src/discovery_runtime/__init__.py','src/discovery_runtime/cli.py','src/discovery_runtime/router.py','src/discovery_runtime/context.py','src/discovery_runtime/state_machine.py','src/discovery_runtime/events.py','src/discovery_runtime/host.py','src/discovery_runtime/contracts.py','src/discovery_runtime/io.py','tests/test_runtime.py','README.md','USAGE.md','CONTRIBUTING.md','TESTING_GUIDE.md','CHANGELOG.md','intents/discover.md','intents/refine.md','intents/validate.md','tracks/build.md','tracks/opportunity.md','tracks/change.md','runtime/state-machine.md','runtime/workstreams.md','runtime/handoff.md','policies/quick-exit.md','policies/capability-negotiation.md','policies/small-model-contract.md','policies/project-constitution.md','policies/scope-decomposition.md','policies/decision-graph.md','policies/approach-comparison.md','policies/clarification-budget.md','policies/approval-contract.md','policies/artifact-graph.md','policies/next-action-selector.md','policies/question-lookahead.md','policies/assumption-budget.md','policies/evidence-management.md','policies/interaction-adaptation.md','policies/stop-policy.md','policies/state-persistence.md','policies/workspace-inspection.md','policies/living-spec-lifecycle.md','policies/claim-ledger.md','policies/visual-validation.md','policies/independent-review.md','policies/model-routing.md','policies/research-orchestration.md','policies/extension-hooks.md','ontology/induction.md','ontology/slot-ranking.md','validators/quick-build.md','validators/standard-build.md','validators/deep-build.md','validators/opportunity.md','validators/change.md','validators/spec-quality.md','validators/implementation-readiness.md','schemas/state.schema.json','schemas/output.schema.json','schemas/living-spec.schema.json','schemas/change-proposal.schema.json','schemas/project-ontology.schema.json','schemas/domain-seed.schema.json','schemas/interview-scenario.schema.json','schemas/eval-run.schema.json','schemas/constitution.schema.json','schemas/coverage-map.schema.json','schemas/extensions.schema.json','schemas/artifact-schemas.schema.json','schemas/visual-options.schema.json','templates/state.yaml','templates/living-spec.yaml','templates/change-proposal.yaml','templates/project-ontology.yaml','templates/constitution.yaml','templates/coverage-map.yaml','templates/extensions.yaml','templates/artifact-schemas.yaml','templates/visual-options.yaml','evals/cases.json','evals/sample-run.json','evals/interview-scenarios.json','evals/grading-rubric.yaml','living-spec/README.md','handoffs/execution-alignment.md','scripts/init_state.py','scripts/init_living_spec.py','scripts/create_change.py','scripts/validate_living_spec.py','scripts/archive_change.py','scripts/init_ontology.py','scripts/validate_eval_corpus.py','scripts/score_transcript.py','scripts/init_constitution.py','scripts/validate_constitution.py','scripts/run_protocol_benchmark.py','scripts/run_external_eval.py','scripts/build_context_index.py','scripts/migrate_artifacts.py','scripts/validate_extensions.py','scripts/validate_artifact_schemas.py','scripts/install_skill.py','scripts/render_visual_options.py','benchmarks/rubric.yaml','benchmarks/README.md']
    required += [f'ontology/seeds/{name}.yaml' for name in ['internal-automation','ai-product','api-integration','data-system','website-ui','enterprise-saas','hardware-iot']]
    required += [str(p.relative_to(ROOT)) for p in (ROOT/'bundles').glob('*.yaml')]
    for r in required:
        if not (ROOT/r).is_file():error(f'missing required file: {r}')
def check_frontmatter():
    fm=load_frontmatter(ROOT/'SKILL.md'); allowed={'name','description','license','compatibility','metadata','allowed-tools'}; unknown=set(fm)-allowed
    if unknown:error(f'SKILL.md unsupported fields: {sorted(unknown)}')
    name=fm.get('name')
    if name!=ROOT.name:error(f"skill name '{name}' does not match directory '{ROOT.name}'")
    if not isinstance(name,str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',name or ''):error('invalid skill name')
    if len(str(fm.get('description','')).strip())<40:error('description too short')
def check_references():
    pat=re.compile(r'`((?:intents|tracks|runtime|policies|ontology|auditors|validators|templates|schemas|examples|scripts|evals|living-spec|handoffs|benchmarks)/[^`]+)`')
    for p in ROOT.rglob('*.md'):
        for ref in pat.findall(p.read_text(encoding='utf-8')):
            clean=ref.strip().split()[0].rstrip('.,;:')
            if any(x in clean for x in ['<','>','*']):continue
            if not (ROOT/clean).exists():error(f'{p.relative_to(ROOT)} references missing path: {clean}')
def check_placeholders():
    for p in ROOT.rglob('*'):
        if p.is_file() and p.suffix.lower() in {'.md','.yaml','.yml','.json'}:
            txt=p.read_text(encoding='utf-8')
            for token in ['INSERT USER','TODO_PLACEHOLDER','PLACEHOLDER_TRANSCRIPT','ALL GREEN']:
                if token in txt:error(f'{p.relative_to(ROOT)} contains forbidden token: {token}')
def check_parseability():
    for p in list(ROOT.rglob('*.yaml'))+list(ROOT.rglob('*.yml')):
        try:yaml.safe_load(p.read_text(encoding='utf-8'))
        except Exception as e:error(f'invalid YAML {p.relative_to(ROOT)}: {e}')
    for p in ROOT.rglob('*.json'):
        try:json.loads(p.read_text(encoding='utf-8'))
        except Exception as e:error(f'invalid JSON {p.relative_to(ROOT)}: {e}')
def validate(data_path,schema_path,label):
    try:
        data=yaml.safe_load((ROOT/data_path).read_text(encoding='utf-8')) if str(data_path).endswith(('.yaml','.yml')) else json.loads((ROOT/data_path).read_text(encoding='utf-8')); schema=json.loads((ROOT/schema_path).read_text(encoding='utf-8'))
        for i in Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(data):error(f'{label} schema at {list(i.path)}: {i.message}')
    except Exception as e:error(f'{label} validation failed: {e}')
def check_schemas():
    validate('templates/llm-action.json','schemas/llm-action.schema.json','llm action template'); validate('templates/request-profile.json','schemas/request-profile.schema.json','request profile template'); validate('templates/state.yaml','schemas/state.schema.json','state template'); validate('templates/living-spec.yaml','schemas/living-spec.schema.json','living spec template'); validate('templates/change-proposal.yaml','schemas/change-proposal.schema.json','change template'); validate('templates/project-ontology.yaml','schemas/project-ontology.schema.json','ontology template'); validate('evals/interview-scenarios.json','schemas/interview-scenario.schema.json','interview corpus')
    validate('evals/sample-run.json','schemas/eval-run.schema.json','sample eval run'); validate('templates/constitution.yaml','schemas/constitution.schema.json','constitution template'); validate('templates/coverage-map.yaml','schemas/coverage-map.schema.json','coverage map template'); validate('templates/extensions.yaml','schemas/extensions.schema.json','extensions template'); validate('templates/artifact-schemas.yaml','schemas/artifact-schemas.schema.json','artifact schema registry'); validate('templates/visual-options.yaml','schemas/visual-options.schema.json','visual options template')
    for name in ['internal-automation','ai-product','api-integration','data-system','website-ui','enterprise-saas','hardware-iot']:
        validate(f'ontology/seeds/{name}.yaml','schemas/domain-seed.schema.json',f'ontology seed {name}')
    out=json.loads((ROOT/'schemas/output.schema.json').read_text(encoding='utf-8')); v=Draft202012Validator(out)
    for n in ['quick-build.yaml','standard-build.yaml','deep-build.yaml','opportunity.yaml','change-delta.yaml']:
        d=yaml.safe_load((ROOT/'templates'/n).read_text(encoding='utf-8'))
        for i in v.iter_errors(d):error(f'templates/{n} schema at {list(i.path)}: {i.message}')
def smoke_scripts():
    env={**__import__('os').environ,'PYTHONPATH':str(ROOT/'src')}
    p=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,text=True,capture_output=True,env=env)
    if p.returncode:error(f'runtime unit tests failed: {p.stdout}{p.stderr}')
    p=subprocess.run([sys.executable,'-m','discovery_runtime.cli','route','--intent','discover','--track','build','--depth','quick','--model-tier','light','--capabilities','none','--workspace','--json'],cwd=ROOT,text=True,capture_output=True,env=env)
    if p.returncode:error(f'policy router smoke failed: {p.stdout}{p.stderr}')
    p=subprocess.run([sys.executable,'-m','discovery_runtime.cli','triage','--profile','@templates/request-profile.json','--json'],cwd=ROOT,text=True,capture_output=True,env=env)
    if p.returncode:error(f'triage smoke failed: {p.stdout}{p.stderr}')
    with tempfile.TemporaryDirectory() as td:
        cmds=[['init_state.py','--workspace',td,'--project-id','smoke','--intent','discover','--track','build','--depth','quick'],['validate_state.py',str(Path(td)/'.discovery/state.yaml')],['init_constitution.py','--workspace',td,'--project-id','smoke'],['validate_constitution.py',str(Path(td)/'.discovery/constitution.yaml')],['build_context_index.py','--workspace',td],['validate_extensions.py',str(ROOT/'templates/extensions.yaml')],['validate_artifact_schemas.py',str(ROOT/'templates/artifact-schemas.yaml')],['run_external_eval.py','--scenario','vba-purchase-import','--runs-dir',str(Path(td)/'runs'),'--dry-run'],['render_visual_options.py',str(ROOT/'templates/visual-options.yaml'),'--output',str(Path(td)/'visual-options.html')],['init_living_spec.py','--workspace',td,'--project-id','smoke'],['create_change.py','--workspace',td,'--title','Smoke change','--intent','discover'],['init_ontology.py','--workspace',td,'--project-id','smoke','--domains','ai-product,api-integration'],['validate_living_spec.py','--workspace',td]]
        for cmd in cmds:
            p=subprocess.run([sys.executable,str(ROOT/'scripts'/cmd[0]),*cmd[1:]],text=True,capture_output=True)
            if p.returncode:error(f"script smoke failed {' '.join(cmd)}: {p.stdout}{p.stderr}")
        p=subprocess.run([sys.executable,str(ROOT/'scripts/run_protocol_benchmark.py'),'--output',str(Path(td)/'protocol-results.yaml')],text=True,capture_output=True)
        if p.returncode:error(f"protocol coverage audit smoke failed: {p.stdout}{p.stderr}")

def main():
    check_required_structure();check_frontmatter();check_references();check_placeholders();check_parseability();check_schemas();
    if os.environ.get('DISCOVERY_FAST_VALIDATE')!='1': smoke_scripts()
    lines=len((ROOT/'SKILL.md').read_text(encoding='utf-8').splitlines())
    if lines>220:warn(f'SKILL.md is {lines} lines')
    print(f'Validated: {ROOT}\nErrors: {len(ERRORS)}');[print('  ERROR:',x) for x in ERRORS];print(f'Warnings: {len(WARNINGS)}');[print('  WARNING:',x) for x in WARNINGS];return 1 if ERRORS else 0
if __name__=='__main__':sys.exit(main())
