from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from .router import RouteResult

@dataclass
class ContextPacket:
    budget_chars: int
    used_chars: int
    loaded_files: list[str]
    deferred_files: list[str]
    content: str
    def to_dict(self): return asdict(self)

def build_context_packet(root: Path, route: RouteResult) -> ContextPacket:
    chunks=[]; loaded=[]; deferred=[]; used=0
    for rel in route.files:
        text=(root/rel).read_text(encoding="utf-8").strip()
        block=f"\n<!-- source: {rel} -->\n{text}\n"
        if used+len(block)<=route.budget_chars or not loaded:
            chunks.append(block); loaded.append(rel); used+=len(block)
        else:
            deferred.append(rel)
    header=("# Discovery Runtime Context Packet\n"
            f"Budget: {route.budget_chars} characters\n"
            f"Loaded: {len(loaded)} files; deferred: {len(deferred)} files.\n"
            "Only the rules in this packet are active for the current node. Read deferred files only when the host routes to them.\n")
    return ContextPacket(route.budget_chars,used,loaded,deferred,header+"".join(chunks))
