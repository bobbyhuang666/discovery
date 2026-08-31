from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from .state_machine import transition, validate_invariants, InvariantError

EVENT_TYPES={"stage_transition","fact_added","claim_added","finding_added","assumption_added","unknown_added","decision_added","decision_resolved","requirement_added","evidence_added","question_accepted","next_action_set","approval_recorded"}
COLLECTION_EVENTS={
 "fact_added":("facts",("id","statement")),
 "claim_added":("claims",("id","statement","source_type")),
 "finding_added":("derived_findings",("id","statement")),
 "assumption_added":("assumptions",("id","statement","impact","reversibility")),
 "unknown_added":("unknowns",("id","statement")),
 "decision_added":("decisions",("id","statement","status")),
 "requirement_added":("requirements",("id","statement","priority")),
 "evidence_added":("evidence",("id","source_type","summary")),
}

def validate_event(event:dict[str,Any])->list[str]:
    errors=[]; kind=event.get("event_type")
    if kind not in EVENT_TYPES: return [f"unsupported event_type: {kind}"]
    if kind=="stage_transition" and not event.get("target_stage"): errors.append("stage_transition requires target_stage")
    if kind in COLLECTION_EVENTS:
        payload=event.get("payload")
        if not isinstance(payload,dict): errors.append(f"{kind} requires object payload")
        else:
            for key in COLLECTION_EVENTS[kind][1]:
                if payload.get(key) in (None,""): errors.append(f"{kind} payload requires {key}")
    if kind=="decision_resolved":
        if not event.get("decision_id"): errors.append("decision_resolved requires decision_id")
        if event.get("resolution") in (None,""): errors.append("decision_resolved requires resolution")
    if kind=="question_accepted":
        payload=event.get("payload")
        if not isinstance(payload,dict) or not payload.get("question") or payload.get("answer") in (None,""): errors.append("question_accepted requires payload.question and payload.answer")
    if kind=="next_action_set":
        payload=event.get("payload")
        if not isinstance(payload,dict) or not payload.get("type") or not payload.get("reason"): errors.append("next_action_set requires payload.type and payload.reason")
    if kind=="approval_recorded":
        payload=event.get("payload")
        if not isinstance(payload,dict) or not payload.get("level") or not payload.get("status"): errors.append("approval_recorded requires payload.level and payload.status")
    return errors

def apply_event(state:dict[str,Any], event:dict[str,Any])->dict[str,Any]:
    problems=validate_event(event)
    if problems: raise ValueError("; ".join(problems))
    kind=event["event_type"]
    if kind=="stage_transition": return transition(state,event["target_stage"])
    new=deepcopy(state); payload=event.get("payload",{})
    if kind in COLLECTION_EVENTS:
        collection=COLLECTION_EVENTS[kind][0]
        existing={x.get("id") for x in new.get(collection,[]) if isinstance(x,dict)}
        if payload.get("id") in existing: raise ValueError(f"duplicate {collection} id: {payload.get('id')}")
        new.setdefault(collection,[]).append(payload)
    elif kind=="decision_resolved":
        did=event["decision_id"]; found=False
        for d in new.get("decisions",[]):
            if isinstance(d,dict) and d.get("id")==did:
                d.update({"status":"resolved","resolution":event["resolution"],"rationale":event.get("rationale"),"evidence_refs":event.get("evidence_refs",[])}); found=True; break
        if not found: raise ValueError(f"decision not found: {did}")
    elif kind=="question_accepted":
        cp=new.setdefault("clarification_pass",{}); cp["asked"]=cp.get("asked",0)+1; cp["accepted"]=cp.get("accepted",0)+1
        new.setdefault("question_history",[]).append(payload)
    elif kind=="next_action_set": new["next_action"]=payload
    elif kind=="approval_recorded": new["approval"]=payload
    new["updated_at"]=datetime.now(timezone.utc).isoformat()
    errors=validate_invariants(new)
    if errors: raise InvariantError("; ".join(errors))
    return new
