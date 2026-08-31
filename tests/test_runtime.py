from __future__ import annotations
import json, tempfile, unittest
from pathlib import Path
import yaml
from discovery_runtime.router import PolicyRouter, RouteRequest
from discovery_runtime.context import build_context_packet
from discovery_runtime.state_machine import transition, TransitionError, InvariantError
from discovery_runtime.events import apply_event
from discovery_runtime.triage import RequestProfile, triage_request
from discovery_runtime.contracts import validate_llm_action

ROOT=Path(__file__).resolve().parents[1]

class TriageTests(unittest.TestCase):
    def test_clear_tiny_request_exits(self):
        r=triage_request(RequestProfile("clear","low","easy",scope="tiny"))
        self.assertEqual(r.outcome,"direct"); self.assertEqual(r.max_questions,0)
    def test_bounded_request_confirms_once(self):
        r=triage_request(RequestProfile("partial","low","easy",scope="bounded"))
        self.assertEqual(r.outcome,"confirm_once"); self.assertEqual(r.max_questions,1)
    def test_high_risk_forces_discovery(self):
        r=triage_request(RequestProfile("clear","high","easy",scope="tiny"))
        self.assertEqual(r.outcome,"discover"); self.assertEqual(r.recommended_depth,"deep")
    def test_explicit_discovery_forces_discovery(self):
        r=triage_request(RequestProfile("clear","low","easy",scope="tiny",user_requested_discovery=True))
        self.assertEqual(r.outcome,"discover")

class RouterTests(unittest.TestCase):
    def test_quick_is_pruned(self):
        r=PolicyRouter(ROOT).route(RouteRequest("discover","build","quick"))
        self.assertIn("policies/quick-exit.md",r.files)
        self.assertIn("policies/next-action-selector.md",r.files)
        self.assertNotIn("policies/research-orchestration.md",r.files)
        self.assertNotIn("policies/project-constitution.md",r.files)
        self.assertLessEqual(len(r.files),10)
    def test_deep_risk_routing(self):
        r=PolicyRouter(ROOT).route(RouteRequest("validate","change","deep",workspace=True,persistence=True,risks=("security","data")))
        self.assertIn("policies/claim-ledger.md",r.files); self.assertIn("auditors/security.md",r.files); self.assertIn("auditors/data.md",r.files)
    def test_context_budget(self):
        r=PolicyRouter(ROOT).route(RouteRequest("discover","build","quick")); p=build_context_packet(ROOT,r); self.assertLessEqual(p.used_chars,p.budget_chars)
    def test_missing_workspace_capability_routes_fallback(self):
        r=PolicyRouter(ROOT).route(RouteRequest("discover","change","quick",workspace=True,capabilities=()))
        self.assertIn("policies/capability-negotiation.md",r.files)
        self.assertNotIn("policies/workspace-inspection.md",r.files)
        self.assertIn("fallback=workspace_unavailable",r.reasons)
    def test_available_workspace_capability_routes_inspection(self):
        r=PolicyRouter(ROOT).route(RouteRequest("discover","change","quick",workspace=True,capabilities=("filesystem",)))
        self.assertIn("policies/workspace-inspection.md",r.files)
    def test_light_model_bundle(self):
        r=PolicyRouter(ROOT).route(RouteRequest("discover","build","quick",model_tier="light"))
        self.assertIn("policies/small-model-contract.md",r.files)

class ContractTests(unittest.TestCase):
    def base_action(self):
        return {"action":"ask","question":"Which option should we use?","recommendation":"A","rationale":"A is reversible.","reversal_conditions":[],"options":["A","B"],"state_events":[],"requested_files":[],"user_visible_message":"Choose A or B.","capability_fallback":None}
    def test_light_rejects_multiple_questions(self):
        a=self.base_action(); a["question"]="First? Second?"
        self.assertTrue(any("one visible question" in x for x in validate_llm_action(a,"light")))
    def test_light_rejects_too_many_options(self):
        a=self.base_action(); a["options"]=["A","B","C","D"]
        self.assertTrue(any("three options" in x for x in validate_llm_action(a,"light")))
    def test_standard_allows_four_options(self):
        a=self.base_action(); a["options"]=["A","B","C","D"]
        self.assertEqual(validate_llm_action(a,"standard"),[])

class StateTests(unittest.TestCase):
    def base(self): return yaml.safe_load((ROOT/"templates/state.yaml").read_text())
    def test_illegal_transition(self):
        with self.assertRaises(TransitionError): transition(self.base(),"ready_for_plan")
    def test_blocking_decision_rejects_ready(self):
        s=self.base(); s["stage"]="discovering"; s["decisions"]=[{"id":"D1","status":"unresolved","impact":"high","reversibility":"hard"}]
        with self.assertRaises(InvariantError): transition(s,"ready_for_spec")
    def test_event_resolution(self):
        s=self.base(); s["stage"]="discovering"; s["decisions"]=[{"id":"D1","status":"unresolved","blocking":True}]
        n=apply_event(s,{"event_type":"decision_resolved","decision_id":"D1","resolution":"A"}); self.assertEqual(n["decisions"][0]["status"],"resolved")
    def test_budget_enforced(self):
        s=self.base(); s["stage"]="discovering"; s["clarification_pass"].update({"max_questions":1,"asked":1,"accepted":1})
        with self.assertRaises(InvariantError): apply_event(s,{"event_type":"question_accepted","payload":{"question":"x","answer":"y"}})

class HostTests(unittest.TestCase):
    def make_host(self, *, capabilities=None, model_tier="standard", stage="orienting"):
        from discovery_runtime.host import DiscoveryHost
        td=tempfile.TemporaryDirectory(); base=Path(td.name); d=base/'.discovery'; d.mkdir()
        state=yaml.safe_load((ROOT/'templates/state.yaml').read_text())
        state['stage']=stage; state['runtime']['model_tier']=model_tier
        if capabilities is not None: state['runtime']['capabilities']=capabilities
        (d/'state.yaml').write_text(yaml.safe_dump(state,sort_keys=False),encoding='utf-8')
        (d/'events.jsonl').write_text('',encoding='utf-8')
        return td, DiscoveryHost(base)
    def test_action_guard_and_revision(self):
        td,host=self.make_host()
        try:
            with self.assertRaises(ValueError): host.apply_action({'action':'plan','rationale':'too early','state_events':[]})
            out=host.apply_action({'action':'inspect','rationale':'inspect first','state_events':[{'event_type':'fact_added','payload':{'id':'F1','statement':'README exists'}}]})
            self.assertEqual(out['runtime']['revision'],1); self.assertEqual(out['facts'][0]['id'],'F1')
            self.assertEqual(len(host.events_path.read_text(encoding='utf-8').splitlines()),1)
        finally: td.cleanup()
    def test_missing_inspection_capability_rejected(self):
        td,host=self.make_host(capabilities=[])
        try:
            with self.assertRaisesRegex(ValueError,"inspect action unavailable"):
                host.apply_action({'action':'inspect','rationale':'inspect first','state_events':[]})
        finally: td.cleanup()
    def test_capability_fallback_only_once(self):
        td,host=self.make_host(capabilities=[],stage="discovering")
        action={'action':'ask','question':'Please upload the file?','recommendation':'Upload the smallest relevant file.','rationale':'Filesystem access is unavailable.','reversal_conditions':[],'options':['Upload','Paste','Continue with assumptions'],'state_events':[],'requested_files':[],'user_visible_message':'I cannot access the workspace. Upload, paste, or continue with assumptions.','capability_fallback':'filesystem'}
        try:
            out=host.apply_action(action); self.assertIn('filesystem',out['runtime']['capability_notices'])
            with self.assertRaisesRegex(ValueError,"already presented"):
                host.apply_action(action)
        finally: td.cleanup()
    def test_light_contract_enforced_by_host(self):
        td,host=self.make_host(model_tier="light",stage="discovering")
        try:
            with self.assertRaisesRegex(ValueError,"one visible question"):
                host.apply_action({'action':'ask','question':'First? Second?','recommendation':'First','rationale':'One at a time.','reversal_conditions':[],'options':[],'state_events':[]})
        finally: td.cleanup()
    def test_pending_log_recovery(self):
        td,host=self.make_host()
        try:
            out=host.apply({'event_type':'fact_added','payload':{'id':'F1','statement':'x'}})
            record=json.loads(host.events_path.read_text().splitlines()[0])
            host.events_path.write_text('',encoding='utf-8')
            host.pending_path.write_text(json.dumps({'record':record}),encoding='utf-8')
            recovery=host.recover_pending(); self.assertEqual(recovery['recovered'],'event_log')
            self.assertEqual(len(host.events_path.read_text(encoding='utf-8').splitlines()),1)
        finally: td.cleanup()

if __name__=="__main__": unittest.main()
