"""Filesystem handoff adapter for a host that can dispatch app subagents."""
from __future__ import annotations

import json
import math
import os
import tempfile
import time
import uuid
import sys
from pathlib import Path
from typing import Any

from jsonschema import SchemaError, ValidationError, validators

from .delivery_executor import ExecutorError


def _atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def mark_abandoned_pending_requests(control_dir: Path) -> int:
    """Mark leftover handoffs abandoned while the caller holds run.lock.

    Only the known delivery request locations are inspected. The caller must
    hold the workspace's exclusive delivery lock before calling this helper;
    a timeout or unreadable response is not evidence that a request is stale.
    """
    control_dir = Path(control_dir)
    if control_dir.is_symlink():
        return 0
    try:
        control_root = control_dir.resolve(strict=True)
    except OSError:
        return 0
    if not control_root.is_dir():
        return 0

    patterns = (
        "revision-*/planning/plan-*/request.json",
        "revision-*/attempt-*/build/build-*/request.json",
        "revision-*/attempt-*/review/review-*/request.json",
    )
    request_paths = sorted({path for pattern in patterns for path in control_root.glob(pattern)})
    abandoned = 0
    for request_path in request_paths:
        safe_path = True
        try:
            relative_parts = request_path.relative_to(control_root).parts
            current_path = control_root
            for part in relative_parts:
                current_path = current_path / part
                if current_path.is_symlink():
                    safe_path = False
                    break
            if not safe_path:
                continue
            resolved_path = request_path.resolve(strict=True)
            resolved_path.relative_to(control_root)
            if not request_path.is_file():
                continue
            request = json.loads(request_path.read_text(encoding="utf-8"))
        except (OSError, RuntimeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(request, dict) or request.get("status") != "pending":
            continue
        request["status"] = "abandoned"
        try:
            _atomic_json(request_path, request)
        except (OSError, TypeError, ValueError):
            raise ExecutorError("Could not mark pending handoff request abandoned") from None
        abandoned += 1
    return abandoned


class HandoffExecutor:
    """Wait for an external host/agent to answer a unique filesystem request."""

    def __init__(
        self,
        model: str | None = None,
        reasoning_effort: str | None = None,
        timeout: float = 900,
    ) -> None:
        try:
            finite_timeout = math.isfinite(timeout) if isinstance(timeout, (int, float)) else False
        except OverflowError:
            finite_timeout = False
        if (
            isinstance(timeout, bool)
            or not finite_timeout
            or timeout <= 0
        ):
            raise ValueError("timeout must be a finite number greater than zero")
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout

    def run(
        self,
        *,
        phase: str,
        prompt: str,
        workspace: Path,
        schema: dict[str, Any],
        log_dir: Path,
    ) -> dict[str, Any]:
        if phase not in {"plan", "build", "review"}:
            raise ExecutorError("Handoff executor received an unsupported phase")
        if not isinstance(prompt, str):
            raise ExecutorError("Handoff executor prompt must be a string")
        if not isinstance(schema, dict):
            raise ExecutorError("Handoff executor schema must be an object")
        try:
            validator_class = validators.validator_for(schema)
            validator_class.check_schema(schema)
            response_validator = validator_class(schema)
        except (SchemaError, TypeError, ValueError):
            raise ExecutorError("Handoff executor schema is invalid") from None

        try:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            request_dir = Path(tempfile.mkdtemp(prefix=f"{phase}-", dir=log_dir))
            response_path = request_dir / "response.json"
            request_path = request_dir / "request.json"
            created_at = time.time()
            request = {
                "id": uuid.uuid4().hex,
                "phase": phase,
                "prompt": prompt,
                "workspace": str(Path(workspace).resolve()),
                "schema": schema,
                "response_path": str(response_path.resolve()),
                "model": self.model,
                "reasoning_effort": self.reasoning_effort,
                "owner_pid": os.getpid(),
                "created_at": created_at,
                "expires_at": created_at + self.timeout,
                "status": "pending",
            }
            _atomic_json(request_path, request)
        except (OSError, TypeError, ValueError):
            raise ExecutorError("Could not prepare handoff request") from None

        print(f"Handoff request: {request_path}", file=sys.stderr, flush=True)
        deadline = time.monotonic() + self.timeout
        try:
            while True:
                if time.monotonic() >= deadline:
                    self._set_status(request_path, request, "timed_out")
                    raise ExecutorError(f"Handoff request timed out after {self.timeout:g} seconds")
                if response_path.is_file():
                    try:
                        response = json.loads(response_path.read_text(encoding="utf-8"))
                    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                        self._set_status(request_path, request, "invalid")
                        raise ExecutorError("Handoff response is malformed JSON") from None
                    if not isinstance(response, dict):
                        self._set_status(request_path, request, "invalid")
                        raise ExecutorError("Handoff response must be a JSON object")
                    try:
                        response_validator.validate(response)
                    except ValidationError:
                        self._set_status(request_path, request, "invalid")
                        raise ExecutorError("Handoff response did not match the schema") from None
                    self._set_status(request_path, request, "completed")
                    return response
                time.sleep(0.1)
        except KeyboardInterrupt:
            self._set_status(request_path, request, "cancelled")
            raise

    @staticmethod
    def _set_status(request_path: Path, request: dict[str, Any], status: str) -> None:
        request["status"] = status
        try:
            _atomic_json(request_path, request)
        except (OSError, TypeError, ValueError):
            raise ExecutorError("Could not update handoff request status") from None
