from __future__ import annotations
from pathlib import PurePosixPath
from typing import Any
from .events import validate_event

VALID_ACTIONS={"ask","inspect","research","test","sketch","prototype","default","summarize","validate","stop","compare","create_spec","plan","block","transition","classify","complete"}
VALID_MODEL_TIERS={"light","standard","strong"}


def _visible_question_count(text: str) -> int:
    return text.count("?") + text.count("？")


def validate_llm_action(data:dict[str,Any], model_tier:str="standard")->list[str]:
    errors=[]; action=data.get("action")
    if model_tier not in VALID_MODEL_TIERS: errors.append(f"invalid model tier: {model_tier}")
    if action not in VALID_ACTIONS: errors.append("invalid or missing action")
    if not data.get("rationale"): errors.append("action requires rationale")
    if action=="ask":
        for k in ["question","recommendation"]:
            if not data.get(k): errors.append(f"ask action requires {k}")
        if not isinstance(data.get("reversal_conditions",[]),list): errors.append("reversal_conditions must be a list")
        options=data.get("options",[])
        if not isinstance(options,list): errors.append("options must be a list")
        elif len(options)>4: errors.append("ask action allows at most four options")
    events=data.get("state_events",[])
    if not isinstance(events,list): errors.append("state_events must be a list")
    else:
        for i,event in enumerate(events):
            if not isinstance(event,dict): errors.append(f"state_events[{i}] must be an object")
            else: errors.extend(f"state_events[{i}]: {x}" for x in validate_event(event))
    files=data.get("requested_files",[])
    if not isinstance(files,list): errors.append("requested_files must be a list")
    else:
        for rel in files:
            p=PurePosixPath(str(rel))
            if p.is_absolute() or ".." in p.parts: errors.append(f"unsafe requested file path: {rel}")

    if model_tier=="light":
        if action=="ask" and _visible_question_count(str(data.get("question") or ""))>1:
            errors.append("light model profile allows one visible question")
        if len(data.get("options",[]))>3:
            errors.append("light model profile allows at most three options")
        if isinstance(events,list) and len(events)>3:
            errors.append("light model profile allows at most three state events")
        if isinstance(files,list) and len(files)>3:
            errors.append("light model profile allows at most three requested files")
        if len(str(data.get("rationale") or ""))>500:
            errors.append("light model rationale exceeds 500 characters")
        if len(str(data.get("user_visible_message") or ""))>900:
            errors.append("light model visible message exceeds 900 characters")
    return errors
