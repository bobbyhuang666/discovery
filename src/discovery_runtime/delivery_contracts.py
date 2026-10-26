"""Small contracts shared by planning, execution and independent review."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse
from jsonschema import Draft202012Validator


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


TEXT = {"type": "string"}
TEXTS = {"type": "array", "items": TEXT}
COMMAND = {"type": "array", "items": TEXT, "minItems": 1}
PLAN = object_schema({
    "title": TEXT, "outcome": TEXT, "scope": TEXTS, "non_goals": TEXTS,
    "assumptions": TEXTS,
    "superseded_acceptance": {"type": "array", "items": object_schema({"id": TEXT, "reason": TEXT})},
    "acceptance": {"type": "array", "minItems": 1, "items": object_schema({
        "id": TEXT, "description": TEXT, "command": COMMAND,
        "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 300},
    })},
    "launch": object_schema({"command": COMMAND, "url": TEXT}),
    "artifacts": {"type": "array", "items": TEXT, "minItems": 1},
})
PLAN_RESPONSE = object_schema({
    "decision": {"enum": ["ready", "needs_input"]}, "question": TEXT,
    "plan": {"anyOf": [PLAN, {"type": "null"}]},
})
BUILD_RESPONSE = object_schema({
    "status": {"enum": ["built", "blocked"]}, "summary": TEXT,
    "blocker": TEXT,
})
REVIEW_RESPONSE = object_schema({
    "verdict": {"enum": ["pass", "revise", "blocked"]},
    "summary": TEXT, "issues": TEXTS,
    "checks": {"type": "array", "items": object_schema({
        "id": TEXT, "passed": {"type": "boolean"}, "evidence": TEXT,
    })},
})


def validate(data, schema):
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: str(e.path))
    if errors:
        raise ValueError("Invalid delivery response: " + "; ".join(e.message for e in errors[:3]))


def local_path(root: Path, value: str) -> Path:
    p = Path(value)
    if not value.strip() or p.is_absolute() or ".." in p.parts or p == Path("."):
        raise ValueError(f"Expected product-relative file path: {value}")
    target = root / p
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes product: {value}")
    return target


def validate_plan(plan):
    # Read plans created before feedback regression tracking was introduced.
    if isinstance(plan, dict):
        plan.setdefault("superseded_acceptance", [])
    validate(plan, PLAN)
    for key in ("title", "outcome"):
        if not plan[key].strip():
            raise ValueError(f"Plan requires {key}")
    if not plan["scope"]:
        raise ValueError("Plan scope cannot be empty")
    ids = [c["id"] for c in plan["acceptance"]]
    if len(ids) != len(set(ids)) or any(not x.strip() for x in ids):
        raise ValueError("Acceptance IDs must be unique and nonempty")
    for check in plan["acceptance"]:
        if not check["description"].strip():
            raise ValueError("Acceptance description cannot be empty")
    for cmd in [plan["launch"]["command"], *[c["command"] for c in plan["acceptance"]]]:
        if not cmd[0].strip() or any("\x00" in arg for arg in cmd):
            raise ValueError("Commands require a valid executable and arguments")
    url = plan["launch"]["url"]
    parsed = urlparse(url.replace("{port}", "8765"))
    authority = url.split("/", 3)[2] if "://" in url else ""
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.port != 8765 or not authority.endswith(":{port}")):
        raise ValueError("Preview URL must be loopback HTTP with a {port} placeholder")
    superseded = [c["id"] for c in plan["superseded_acceptance"]]
    if len(superseded) != len(set(superseded)) or any(not c["reason"].strip() for c in plan["superseded_acceptance"]):
        raise ValueError("Superseded acceptance IDs must be unique and have a reason")
    for item in plan["artifacts"]:
        # Actual symlink containment is also checked against the product at runtime.
        local_path(Path.cwd(), item)


def validate_review(review, plan):
    validate(review, REVIEW_RESPONSE)
    expected = {c["id"] for c in plan["acceptance"]}
    ids = [c["id"] for c in review["checks"]]
    if set(ids) != expected or len(ids) != len(expected):
        raise ValueError("Independent review must cover each acceptance ID exactly once")
    if any(not c["evidence"].strip() for c in review["checks"]):
        raise ValueError("Independent review requires evidence for every check")
    if review["verdict"] == "pass" and (review["issues"] or not all(c["passed"] for c in review["checks"])):
        raise ValueError("Passing review contains unresolved issues or failed checks")
