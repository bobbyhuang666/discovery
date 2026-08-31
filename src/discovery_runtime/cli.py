from __future__ import annotations
import argparse, json, sys, os
from pathlib import Path
from .router import PolicyRouter, RouteRequest
from .context import build_context_packet
from .host import DiscoveryHost
from .state_machine import allowed_actions, validate_invariants
from .contracts import validate_llm_action
from .triage import RequestProfile, triage_request
from .io import load_yaml

def skill_root()->Path:
    candidates=[]
    if os.environ.get("DISCOVERY_SKILL_ROOT"): candidates.append(Path(os.environ["DISCOVERY_SKILL_ROOT"]))
    candidates.extend([Path.cwd(), Path(__file__).resolve().parents[2]])
    for candidate in candidates:
        if (candidate/"routes.yaml").is_file(): return candidate.resolve()
    raise FileNotFoundError("Discovery skill root not found; run from the skill directory or set DISCOVERY_SKILL_ROOT")

def flags(values): return tuple(x.strip() for x in (values or "").split(",") if x.strip())
def parse_capabilities(values):
    if values is None: return None
    if values.strip().lower() in {"", "none"}: return ()
    return flags(values)
def read_json_arg(value:str):
    raw=Path(value[1:]).read_text(encoding="utf-8") if value.startswith("@") else value
    return json.loads(raw)
def route_req(a):
    return RouteRequest(a.intent,a.track,a.depth,a.workspace,a.persistence,a.extensions,a.visual,a.research,flags(a.risks),parse_capabilities(a.capabilities),a.model_tier,not a.no_quick_exit)
def add_route_args(p):
    p.add_argument("--intent",choices=["discover","refine","validate"],required=True); p.add_argument("--track",choices=["build","opportunity","change"],required=True); p.add_argument("--depth",choices=["quick","standard","deep"],required=True)
    for x in ["workspace","persistence","extensions","visual","research"]: p.add_argument(f"--{x}",action="store_true")
    p.add_argument("--risks",default="")
    p.add_argument("--capabilities",default=None,help="Comma-separated runtime capabilities, 'none', or omit for legacy auto-assume")
    p.add_argument("--model-tier",choices=["light","standard","strong"],default="standard")
    p.add_argument("--no-quick-exit",action="store_true")
def main(argv=None)->int:
    ap=argparse.ArgumentParser(prog="discovery"); sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("triage"); p.add_argument("--profile",required=True,help="JSON string or @file"); p.add_argument("--json",action="store_true")
    p=sub.add_parser("route"); add_route_args(p); p.add_argument("--json",action="store_true")
    p=sub.add_parser("build-context"); add_route_args(p); p.add_argument("--output")
    p=sub.add_parser("allowed-actions"); p.add_argument("--state",default=".discovery/state.yaml")
    p=sub.add_parser("transition"); p.add_argument("--workspace",default="."); p.add_argument("--to",required=True)
    p=sub.add_parser("apply-event"); p.add_argument("--workspace",default="."); p.add_argument("--event",required=True,help="JSON string or @file")
    p=sub.add_parser("apply-action"); p.add_argument("--workspace",default="."); p.add_argument("--action",required=True,help="JSON string or @file")
    p=sub.add_parser("recover"); p.add_argument("--workspace",default=".")
    p=sub.add_parser("validate-state"); p.add_argument("--state",default=".discovery/state.yaml")
    p=sub.add_parser("validate-action"); p.add_argument("--action",required=True,help="JSON string or @file"); p.add_argument("--model-tier",choices=["light","standard","strong"],default="standard")
    a=ap.parse_args(argv); root=skill_root()
    if a.cmd=="triage":
        result=triage_request(RequestProfile.from_dict(read_json_arg(a.profile)))
        data=result.to_dict(); print(json.dumps(data,indent=2,ensure_ascii=False) if a.json else f"{data['outcome']}\n"+"\n".join(data['reasons'])); return 0
    if a.cmd in {"route","build-context"}:
        result=PolicyRouter(root).route(route_req(a))
        if a.cmd=="route":
            data={"files":result.files,"bundles":result.bundles,"budget_chars":result.budget_chars,"reasons":result.reasons}; print(json.dumps(data,indent=2) if a.json else "\n".join(result.files)); return 0
        packet=build_context_packet(root,result)
        if a.output: Path(a.output).write_text(packet.content,encoding="utf-8")
        else: print(packet.content)
        print(json.dumps({k:v for k,v in packet.to_dict().items() if k!="content"},indent=2),file=sys.stderr); return 0
    if a.cmd=="allowed-actions": print(json.dumps(allowed_actions(load_yaml(Path(a.state))),indent=2)); return 0
    if a.cmd=="transition": print(json.dumps(DiscoveryHost(Path(a.workspace)).apply({"event_type":"stage_transition","target_stage":a.to}),indent=2)); return 0
    if a.cmd=="apply-event": print(json.dumps(DiscoveryHost(Path(a.workspace)).apply(read_json_arg(a.event)),indent=2)); return 0
    if a.cmd=="apply-action": print(json.dumps(DiscoveryHost(Path(a.workspace)).apply_action(read_json_arg(a.action)),indent=2)); return 0
    if a.cmd=="recover": print(json.dumps(DiscoveryHost(Path(a.workspace)).recover_pending(),indent=2)); return 0
    if a.cmd=="validate-state":
        errs=validate_invariants(load_yaml(Path(a.state))); print("VALID" if not errs else "\n".join(errs)); return 1 if errs else 0
    if a.cmd=="validate-action":
        errs=validate_llm_action(read_json_arg(a.action),model_tier=a.model_tier); print("VALID" if not errs else "\n".join(errs)); return 1 if errs else 0
    return 2
if __name__=="__main__": raise SystemExit(main())
