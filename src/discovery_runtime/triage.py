from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any

VALID_CLARITY = {"clear", "partial", "unclear"}
VALID_RISK = {"low", "medium", "high"}
VALID_REVERSIBILITY = {"easy", "moderate", "hard"}
VALID_SCOPE = {"tiny", "bounded", "large"}


@dataclass(frozen=True)
class RequestProfile:
    clarity: str
    risk: str
    reversibility: str
    scope: str = "bounded"
    sensitive_data: bool = False
    external_side_effect: bool = False
    workspace_uncertainty: bool = False
    material_uncertainty: bool = False
    user_requested_discovery: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RequestProfile":
        profile = cls(**data)
        profile.validate()
        return profile

    def validate(self) -> None:
        if self.clarity not in VALID_CLARITY:
            raise ValueError(f"invalid clarity: {self.clarity}")
        if self.risk not in VALID_RISK:
            raise ValueError(f"invalid risk: {self.risk}")
        if self.reversibility not in VALID_REVERSIBILITY:
            raise ValueError(f"invalid reversibility: {self.reversibility}")
        if self.scope not in VALID_SCOPE:
            raise ValueError(f"invalid scope: {self.scope}")


@dataclass(frozen=True)
class TriageResult:
    outcome: str
    recommended_depth: str | None
    reasons: tuple[str, ...]
    max_questions: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def triage_request(profile: RequestProfile) -> TriageResult:
    profile.validate()
    reasons: list[str] = []

    if profile.user_requested_discovery:
        reasons.append("user explicitly requested discovery")
    if profile.material_uncertainty:
        reasons.append("material uncertainty remains")
    if profile.clarity == "unclear":
        reasons.append("request is unclear")
    if profile.risk == "high":
        reasons.append("risk is high")
    if profile.reversibility == "hard":
        reasons.append("decision is hard to reverse")
    if profile.sensitive_data:
        reasons.append("sensitive data is involved")
    if profile.external_side_effect:
        reasons.append("external or irreversible side effect is possible")
    if profile.scope == "large":
        reasons.append("scope requires decomposition")

    if reasons:
        depth = "deep" if any(
            [profile.risk == "high", profile.reversibility == "hard", profile.sensitive_data, profile.scope == "large"]
        ) else "standard"
        return TriageResult("discover", depth, tuple(reasons), 5)

    if (
        profile.clarity == "clear"
        and profile.risk == "low"
        and profile.reversibility == "easy"
        and profile.scope == "tiny"
        and not profile.workspace_uncertainty
    ):
        return TriageResult(
            "direct",
            None,
            ("clear, low-risk, tiny, reversible request with no material unknowns",),
            0,
        )

    return TriageResult(
        "confirm_once",
        "quick",
        ("request is bounded but one material confirmation may still prevent avoidable rework",),
        1,
    )
