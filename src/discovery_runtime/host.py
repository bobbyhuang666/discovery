from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib, json, uuid
from .io import load_yaml, atomic_write_yaml, append_jsonl, file_lock
from .events import apply_event
from .state_machine import validate_invariants, allowed_actions
from .contracts import validate_llm_action

class DiscoveryHost:
    def __init__(self, workspace:Path):
        self.workspace=workspace.resolve(); self.dir=self.workspace/".discovery"
        self.state_path=self.dir/"state.yaml"; self.events_path=self.dir/"events.jsonl"; self.pending_path=self.dir/"pending-event.json"
    def load(self)->dict[str,Any]: return load_yaml(self.state_path)
    @staticmethod
    def digest(state:dict[str,Any])->str:
        raw=json.dumps(state,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode(); return hashlib.sha256(raw).hexdigest()
    def recover_pending(self)->dict[str,Any]|None:
        if not self.pending_path.exists(): return None
        pending=json.loads(self.pending_path.read_text(encoding="utf-8")); state=self.load(); record=pending.get("record",pending.get("event",{}))
        if state.get("last_event_id")==record.get("event_id"):
            append_jsonl(self.events_path,record); self.pending_path.unlink(); return {"recovered":"event_log","event_id":state.get("last_event_id")}
        return {"recovered":"none","reason":"pending record was not committed to state","event_id":record.get("event_id")}
    def _commit(self,before:dict[str,Any],after:dict[str,Any],record:dict[str,Any])->dict[str,Any]:
        before_rev=int((before.get("runtime") or {}).get("revision",0)); event_id=record.setdefault("event_id",str(uuid.uuid4()))
        record.setdefault("timestamp",datetime.now(timezone.utc).isoformat()); after.setdefault("runtime",{})["revision"]=before_rev+1
        after["runtime"]["last_committed_at"]=datetime.now(timezone.utc).isoformat(); after["last_event_id"]=event_id
        record["before_revision"]=before_rev; record["after_revision"]=before_rev+1; record["state_sha256"]=self.digest(after)
        errors=validate_invariants(after)
        if errors: raise ValueError("; ".join(errors))
        self.pending_path.write_text(json.dumps({"record":record},indent=2,ensure_ascii=False),encoding="utf-8")
        atomic_write_yaml(self.state_path,after); append_jsonl(self.events_path,record); self.pending_path.unlink(); return after
    def apply(self,event:dict[str,Any])->dict[str,Any]:
        self.dir.mkdir(parents=True,exist_ok=True)
        with file_lock(self.state_path):
            self._recover_or_fail(); before=self.load(); after=apply_event(before,event); return self._commit(before,after,dict(event))
    def _validate_capability_action(self, action:dict[str,Any], state:dict[str,Any])->list[str]:
        runtime=state.get("runtime") or {}; capabilities=set(runtime.get("capabilities") or [])
        errors=[]
        if action.get("action")=="inspect" and not capabilities.intersection({"filesystem","code_search"}):
            errors.append("inspect action unavailable without filesystem or code_search capability")
        if action.get("action")=="research" and "web" not in capabilities:
            errors.append("research action unavailable without web capability")
        fallback=action.get("capability_fallback")
        if fallback and fallback in set(runtime.get("capability_notices") or []):
            errors.append(f"capability fallback already presented: {fallback}")
        return errors
    def apply_action(self,action:dict[str,Any])->dict[str,Any]:
        self.dir.mkdir(parents=True,exist_ok=True)
        with file_lock(self.state_path):
            self._recover_or_fail(); before=self.load(); runtime=before.get("runtime") or {}
            model_tier=runtime.get("model_tier","standard")
            problems=validate_llm_action(action,model_tier=model_tier)
            problems.extend(self._validate_capability_action(action,before))
            if problems: raise ValueError("; ".join(problems))
            current=before.get("stage")
            if action["action"] not in allowed_actions(before): raise ValueError(f"action {action['action']} not allowed in stage {current}")
            after=before
            for event in action.get("state_events",[]): after=apply_event(after,event)
            fallback=action.get("capability_fallback")
            if fallback:
                after.setdefault("runtime",{}).setdefault("capability_notices",[]).append(fallback)
            record={"event_type":"llm_action_committed","action":action["action"],"decision_id":action.get("decision_id"),"rationale":action.get("rationale"),"capability_fallback":fallback,"state_events":action.get("state_events",[])}
            return self._commit(before,after,record)
    def _recover_or_fail(self):
        if self.pending_path.exists():
            recovery=self.recover_pending()
            if recovery and recovery.get("recovered")=="none": raise RuntimeError("unresolved pending record exists; inspect .discovery/pending-event.json")
