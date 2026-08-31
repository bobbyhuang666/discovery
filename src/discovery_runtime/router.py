from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .io import load_yaml

VALID_INTENTS={"discover","refine","validate"}
VALID_TRACKS={"build","opportunity","change"}
VALID_DEPTHS={"quick","standard","deep"}
VALID_MODEL_TIERS={"light","standard","strong"}
VALID_CAPABILITIES={"filesystem","code_search","command_execution","web","visual_rendering","persistence"}

@dataclass(frozen=True)
class RouteRequest:
    intent: str
    track: str
    depth: str
    workspace: bool=False
    persistence: bool=False
    extensions: bool=False
    visual: bool=False
    research: bool=False
    risks: tuple[str,...]=()
    capabilities: tuple[str,...]|None=None
    model_tier: str="standard"
    include_quick_exit: bool=True

@dataclass
class RouteResult:
    files: list[str]
    bundles: list[str]
    budget_chars: int
    reasons: list[str]

class PolicyRouter:
    def __init__(self, skill_root: Path):
        self.root=skill_root
        self.config=load_yaml(skill_root/"routes.yaml")

    def _has(self, req: RouteRequest, *caps: str) -> bool:
        if req.capabilities is None:
            return True
        return any(cap in req.capabilities for cap in caps)

    def route(self, req: RouteRequest) -> RouteResult:
        if req.intent not in VALID_INTENTS: raise ValueError(f"invalid intent: {req.intent}")
        if req.track not in VALID_TRACKS: raise ValueError(f"invalid track: {req.track}")
        if req.depth not in VALID_DEPTHS: raise ValueError(f"invalid depth: {req.depth}")
        if req.model_tier not in VALID_MODEL_TIERS: raise ValueError(f"invalid model tier: {req.model_tier}")
        if req.capabilities is not None:
            unknown=set(req.capabilities)-VALID_CAPABILITIES
            if unknown: raise ValueError(f"invalid capabilities: {sorted(unknown)}")

        files=[x.format(intent=req.intent,track=req.track,depth=req.depth) for x in self.config["bootstrap"]]
        files += self.config["validators"][req.track][req.depth]
        bundles=[]
        if req.include_quick_exit:
            bundles.append("quick-exit")
        bundles.extend(self.config["depth_bundles"][req.depth])
        cond=[]
        fallbacks=[]

        if req.workspace:
            if self._has(req,"filesystem","code_search"): cond.append("workspace")
            else: fallbacks.append("workspace_unavailable")
        if req.persistence:
            if self._has(req,"filesystem","persistence"): cond.append("persistence")
            else: fallbacks.append("persistence_unavailable")
        if req.extensions: cond.append("extensions")
        if req.visual:
            if self._has(req,"visual_rendering") or (self._has(req,"filesystem") and self._has(req,"command_execution")):
                cond.append("visual")
            else: fallbacks.append("visual_unavailable")
        if req.track=="change": cond.append("change")
        if req.research:
            if self._has(req,"web"): cond.append("research")
            else: fallbacks.append("research_unavailable")
        for risk in req.risks:
            if risk in self.config["conditional_bundles"]: cond.append(risk)
        if req.model_tier=="light": bundles.append("small-model")
        if fallbacks: bundles.append("capability-fallback")

        bundles.extend(self.config["conditional_bundles"][x] for x in cond)
        dedup_b=[]
        for b in bundles:
            if b not in dedup_b: dedup_b.append(b)
        for b in dedup_b:
            manifest=load_yaml(self.root/"bundles"/f"{b}.yaml")
            files.extend(manifest["files"])
        dedup=[]
        for f in files:
            if f not in dedup: dedup.append(f)
        missing=[f for f in dedup if not (self.root/f).is_file()]
        if missing: raise FileNotFoundError("route references missing files: "+", ".join(missing))
        reasons=[f"intent={req.intent}",f"track={req.track}",f"depth={req.depth}",f"model_tier={req.model_tier}"]
        reasons.extend(f"condition={x}" for x in cond)
        reasons.extend(f"fallback={x}" for x in fallbacks)
        if req.capabilities is not None:
            reasons.append("capabilities="+( ",".join(req.capabilities) if req.capabilities else "none"))
        return RouteResult(dedup,dedup_b,int(self.config["context_budgets"][req.depth]),reasons)
