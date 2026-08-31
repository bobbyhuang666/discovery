from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

ALLOWED_TRANSITIONS={
 "orienting":{"discovering","validating","blocked"},
 "discovering":{"resolving","awaiting_user","validating","ready_for_spec","blocked"},
 "resolving":{"discovering","awaiting_user","validating","blocked"},
 "awaiting_user":{"discovering","resolving","blocked"},
 "validating":{"discovering","ready_for_spec","ready_for_plan","blocked","complete"},
 "ready_for_spec":{"validating","ready_for_plan","complete"},
 "ready_for_plan":{"validating","complete"},
 "blocked":{"orienting","discovering","complete"},
 "complete":set(),
}
ALLOWED_ACTIONS={
 "orienting":{"inspect","classify","block"},
 "discovering":{"ask","inspect","research","test","sketch","prototype","default","summarize","validate","block"},
 "resolving":{"ask","inspect","research","test","compare","default","summarize","validate","block"},
 "awaiting_user":{"ask","summarize","block"},
 "validating":{"inspect","test","validate","transition","block"},
 "ready_for_spec":{"create_spec","validate","transition"},
 "ready_for_plan":{"plan","validate","transition"},
 "blocked":{"inspect","ask","transition","complete"},
 "complete":set(),
}

DEFAULT_ACTION={
 "orienting":"inspect","discovering":"inspect","resolving":"ask","awaiting_user":"ask",
 "validating":"validate","ready_for_spec":"create_spec","ready_for_plan":"plan","blocked":"inspect","complete":None,
}

class TransitionError(ValueError): pass
class InvariantError(ValueError): pass

def unresolved_blocking_decisions(state:dict[str,Any])->list[dict[str,Any]]:
    out=[]
    for d in state.get("decisions",[]):
        if not isinstance(d,dict): continue
        if d.get("status","unresolved") in {"resolved","deferred","not_applicable"}: continue
        if d.get("blocking") is True or (d.get("impact")=="high" and d.get("reversibility") in {"hard","difficult"}): out.append(d)
    return out

def p0_without_acceptance(state:dict[str,Any])->list[Any]:
    bad=[]
    for r in state.get("requirements",[]):
        if not isinstance(r,dict) or str(r.get("priority","")).upper()!="P0": continue
        ac=r.get("acceptance_criteria") or r.get("acceptance_tests")
        if not ac: bad.append(r)
    return bad

def validate_invariants(state:dict[str,Any])->list[str]:
    errors=[]; stage=state.get("stage")
    if stage not in ALLOWED_TRANSITIONS: errors.append(f"unknown stage: {stage}")
    cp=state.get("clarification_pass",{})
    if cp.get("asked",0)>cp.get("max_questions",5): errors.append("clarification budget exceeded")
    if cp.get("accepted",0)>cp.get("asked",0): errors.append("accepted questions exceed asked questions")
    if stage in {"ready_for_spec","ready_for_plan","complete"} and unresolved_blocking_decisions(state): errors.append("blocking decisions remain unresolved")
    if stage=="ready_for_plan" and state.get("track")=="build" and p0_without_acceptance(state): errors.append("P0 requirements lack acceptance criteria")
    action=(state.get("next_action") or {}).get("type")
    if action and stage in ALLOWED_ACTIONS and action not in ALLOWED_ACTIONS[stage]: errors.append(f"action {action} not allowed in stage {stage}")
    return errors

def transition(state:dict[str,Any], target:str)->dict[str,Any]:
    current=state.get("stage")
    if target not in ALLOWED_TRANSITIONS.get(current,set()): raise TransitionError(f"illegal transition: {current} -> {target}")
    new=deepcopy(state); new["stage"]=target; new["updated_at"]=datetime.now(timezone.utc).isoformat()
    default=DEFAULT_ACTION.get(target)
    new["next_action"]={"type":default,"target":None,"reason":f"Host default for stage {target}","decision_id":None,"expected_branching_value":"not_applicable"} if default else {"type":None,"target":None,"reason":"Stage complete","decision_id":None,"expected_branching_value":"not_applicable"}
    errors=validate_invariants(new)
    if errors: raise InvariantError("; ".join(errors))
    return new

def allowed_actions(state:dict[str,Any])->list[str]: return sorted(ALLOWED_ACTIONS.get(state.get("stage"),set()))
