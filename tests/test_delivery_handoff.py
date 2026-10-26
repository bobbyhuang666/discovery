from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from discovery_runtime.delivery_executor import ExecutorError
from discovery_runtime.delivery_handoff import HandoffExecutor, mark_abandoned_pending_requests


SCHEMA = {
    "type": "object",
    "properties": {"answer": {"type": "string"}},
    "required": ["answer"],
    "additionalProperties": False,
}


def write_response(path: Path, response: dict) -> None:
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(response), encoding="utf-8")
    os.replace(temp_path, path)


class HandoffExecutorTests(unittest.TestCase):
    def _run(self, executor: HandoffExecutor, log_dir: Path) -> dict:
        return executor.run(
            phase="plan",
            prompt="Make a small local tool.",
            workspace=log_dir.parent / "product",
            schema=SCHEMA,
            log_dir=log_dir,
        )

    def _respond_when_requested(self, log_dir: Path, response: dict) -> threading.Thread:
        errors: list[Exception] = []

        def respond() -> None:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                requests = list(log_dir.glob("plan-*/request.json"))
                if requests:
                    try:
                        request = json.loads(requests[0].read_text(encoding="utf-8"))
                        write_response(Path(request["response_path"]), response)
                    except Exception as exc:  # surfaced to the test after join
                        errors.append(exc)
                    return
                time.sleep(0.01)
            errors.append(TimeoutError("handoff request was not created"))

        thread = threading.Thread(target=respond, daemon=True)
        thread.start()
        thread.errors = errors
        return thread

    def test_threaded_host_writes_unique_response_and_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory) / "logs"
            executor = HandoffExecutor(model="gpt-6-luna", reasoning_effort="high", timeout=2)
            thread = self._respond_when_requested(log_dir, {"answer": "ready"})
            stderr = StringIO()
            with redirect_stderr(stderr):
                result = self._run(executor, log_dir)
            thread.join(timeout=1)

            self.assertFalse(thread.is_alive())
            self.assertEqual(thread.errors, [])
            self.assertEqual(result, {"answer": "ready"})
            request_paths = list(log_dir.glob("plan-*/request.json"))
            self.assertEqual(len(request_paths), 1)
            request = json.loads(request_paths[0].read_text(encoding="utf-8"))
            self.assertEqual(request["status"], "completed")
            self.assertEqual(request["phase"], "plan")
            self.assertEqual(request["prompt"], "Make a small local tool.")
            self.assertEqual(request["model"], "gpt-6-luna")
            self.assertEqual(request["reasoning_effort"], "high")
            self.assertEqual(request["owner_pid"], os.getpid())
            self.assertIsInstance(request["created_at"], (int, float))
            self.assertIsInstance(request["expires_at"], (int, float))
            self.assertAlmostEqual(request["expires_at"] - request["created_at"], 2)
            self.assertTrue(Path(request["response_path"]).is_file())
            self.assertIn(str(request_paths[0]), stderr.getvalue())

    def test_invalid_response_is_rejected_and_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory) / "logs"
            executor = HandoffExecutor(timeout=2)
            thread = self._respond_when_requested(log_dir, {"answer": 3})
            with redirect_stderr(StringIO()):
                with self.assertRaisesRegex(ExecutorError, "did not match the schema"):
                    self._run(executor, log_dir)
            thread.join(timeout=1)
            self.assertEqual(thread.errors, [])
            request_path = next(log_dir.glob("plan-*/request.json"))
            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(request["status"], "invalid")

    def test_timeout_marks_request(self):
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory) / "logs"
            executor = HandoffExecutor(timeout=0.01)
            with redirect_stderr(StringIO()):
                with self.assertRaisesRegex(ExecutorError, "timed out"):
                    self._run(executor, log_dir)
            request_path = next(log_dir.glob("plan-*/request.json"))
            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(request["status"], "timed_out")

    def test_timeout_must_be_finite_positive_numeric(self):
        for timeout in (True, False, 0, -1, math.nan, math.inf, -math.inf, "1", None, 10**1000):
            with self.subTest(timeout=repr(timeout)):
                with self.assertRaisesRegex(ValueError, "finite number greater than zero"):
                    HandoffExecutor(timeout=timeout)

    def test_deadline_wins_over_a_response_written_after_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory) / "logs"
            real_sleep = time.sleep

            def write_late_response(_interval: float) -> None:
                real_sleep(0.05)
                request_path = next(log_dir.glob("plan-*/request.json"))
                request = json.loads(request_path.read_text(encoding="utf-8"))
                write_response(Path(request["response_path"]), {"answer": "too late"})

            with redirect_stderr(StringIO()):
                with patch("discovery_runtime.delivery_handoff.time.sleep", side_effect=write_late_response):
                    with self.assertRaisesRegex(ExecutorError, "timed out"):
                        self._run(HandoffExecutor(timeout=0.01), log_dir)

            request_path = next(log_dir.glob("plan-*/request.json"))
            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertTrue(Path(request["response_path"]).is_file())
            self.assertEqual(request["status"], "timed_out")

    def test_cancellation_marks_request(self):
        with tempfile.TemporaryDirectory() as directory:
            log_dir = Path(directory) / "logs"
            executor = HandoffExecutor(timeout=2)
            with redirect_stderr(StringIO()):
                with patch("discovery_runtime.delivery_handoff.time.sleep", side_effect=KeyboardInterrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        self._run(executor, log_dir)
            request_path = next(log_dir.glob("plan-*/request.json"))
            request = json.loads(request_path.read_text(encoding="utf-8"))
            self.assertEqual(request["status"], "cancelled")

    def test_abandoned_pending_request_from_killed_owner_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            control_dir = Path(directory) / ".delivery"
            request_path = (
                control_dir / "revision-1" / "attempt-1" / "build" / "build-dead-owner" / "request.json"
            )
            response_path = request_path.parent / "response.json"
            owner = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
            try:
                request_path.parent.mkdir(parents=True)
                original_request = {
                    "id": "stale-request",
                    "phase": "build",
                    "prompt": "Build the product.",
                    "workspace": str(Path(directory) / "product"),
                    "schema": SCHEMA,
                    "response_path": str(response_path),
                    "owner_pid": owner.pid,
                    "created_at": 1_800_000_000.0,
                    "expires_at": 1_800_000_900.0,
                    "status": "pending",
                }
                request_path.write_text(json.dumps(original_request), encoding="utf-8")
                response_path.write_text('{"answer":"already written"}', encoding="utf-8")
            finally:
                owner.terminate()
                owner.wait(timeout=3)

            completed_path = (
                control_dir / "revision-1" / "attempt-2" / "review" / "review-complete" / "request.json"
            )
            completed_path.parent.mkdir(parents=True)
            completed_request = {"id": "completed-request", "status": "completed"}
            completed_path.write_text(json.dumps(completed_request), encoding="utf-8")
            unrelated_path = control_dir / "misc" / "request.json"
            unrelated_path.parent.mkdir(parents=True)
            unrelated_request = {"id": "unrelated", "status": "pending"}
            unrelated_path.write_text(json.dumps(unrelated_request), encoding="utf-8")

            self.assertEqual(mark_abandoned_pending_requests(control_dir), 1)

            expected_request = {**original_request, "status": "abandoned"}
            self.assertEqual(json.loads(request_path.read_text(encoding="utf-8")), expected_request)
            self.assertEqual(response_path.read_text(encoding="utf-8"), '{"answer":"already written"}')
            self.assertEqual(json.loads(completed_path.read_text(encoding="utf-8")), completed_request)
            self.assertEqual(json.loads(unrelated_path.read_text(encoding="utf-8")), unrelated_request)


if __name__ == "__main__":
    unittest.main()
