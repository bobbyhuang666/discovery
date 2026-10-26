from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from discovery_runtime.delivery_executor import CodexExecutor, ExecutorError


FAKE_CODEX = r'''#!/usr/bin/env python3
import json
import pathlib
import subprocess
import sys
import time

here = pathlib.Path(__file__).parent
args = sys.argv[1:]
(here / "args.json").write_text(json.dumps(args), encoding="utf-8")
mode = (here / "mode.txt").read_text(encoding="utf-8").strip()
result_path = pathlib.Path(args[args.index("--output-last-message") + 1])

if mode == "timeout":
    # Exercise readiness independently from the executor's two-second timeout.
    time.sleep(2.5)
    result_path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    child_script = here / "child_runner.py"
    child_script.write_text(
        "import pathlib, sys, time\n"
        "marker = pathlib.Path(sys.argv[1])\n"
        "while True:\n"
        "    with marker.open('a', encoding='utf-8') as stream: stream.write('x')\n"
        "    time.sleep(0.02)\n",
        encoding="utf-8",
    )
    child = subprocess.Popen([sys.executable, str(child_script), str(here / "alive.txt")])
    (here / "child.pid").write_text(str(child.pid), encoding="utf-8")

(here / "stdin.txt").write_text(sys.stdin.read(), encoding="utf-8")
print("fake stdout")
print("fake stderr", file=sys.stderr)

if mode in {"success", "nonzero", "invalid_response"}:
    result = {"ok": "not-a-boolean" if mode == "invalid_response" else True}
    result_path.write_text(json.dumps(result), encoding="utf-8")
if mode == "nonzero":
    raise SystemExit(17)
if mode == "timeout":
    while True:
        time.sleep(1)
'''


SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


class CodexExecutorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.log_dir = self.root / "logs"
        self.fake_codex = self.root / "fake-codex"
        self.fake_codex.write_text(FAKE_CODEX.replace("#!/usr/bin/env python3", f"#!{sys.executable}", 1), encoding="utf-8")
        self.fake_codex.chmod(0o755)
        self.mode_file = self.root / "mode.txt"
        self.mode_file.write_text("success", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def executor(self, *, timeout: float = 5) -> CodexExecutor:
        return CodexExecutor(executable=str(self.fake_codex), timeout=timeout)

    def invocations(self) -> list[Path]:
        if not self.log_dir.is_dir():
            return []
        return sorted(path for path in self.log_dir.iterdir() if path.is_dir())

    def test_uses_safe_flags_and_persists_prompt_and_logs(self) -> None:
        prompt = "Build the small app for café users."
        result = CodexExecutor(
            executable=str(self.fake_codex),
            model="gpt-6-luna",
            reasoning_effort="max",
            timeout=5,
        ).run(
            phase="build",
            prompt=prompt,
            workspace=self.workspace,
            schema=SCHEMA,
            log_dir=self.log_dir,
        )

        self.assertEqual(result, {"ok": True})
        invocation = self.invocations()[0]
        args = json.loads((self.root / "args.json").read_text(encoding="utf-8"))
        self.assertEqual((self.root / "stdin.txt").read_text(encoding="utf-8"), prompt)
        self.assertEqual((invocation / "prompt.txt").read_text(encoding="utf-8"), prompt)
        self.assertEqual(json.loads((invocation / "schema.json").read_text()), SCHEMA)
        self.assertEqual(json.loads((invocation / "result.json").read_text()), result)
        self.assertEqual((invocation / "stdout.log").read_text().strip(), "fake stdout")
        self.assertEqual((invocation / "stderr.log").read_text().strip(), "fake stderr")

        self.assertEqual(args[0], "exec")
        self.assertIn("--ephemeral", args)
        self.assertIn("--skip-git-repo-check", args)
        self.assertEqual(args[args.index("--color") + 1], "never")
        self.assertEqual(args[args.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(args[args.index("-C") + 1], str(self.workspace.resolve()))
        self.assertTrue(Path(args[args.index("--output-schema") + 1]).is_file())
        self.assertEqual(
            args[args.index("--output-last-message") + 1],
            str(invocation / "result.json"),
        )
        self.assertEqual(args[args.index("-m") + 1], "gpt-6-luna")
        self.assertEqual(
            args[args.index("-c") + 1], 'model_reasoning_effort="max"'
        )
        self.assertEqual(args[-1], "-")

    def test_plan_and_review_use_read_only_sandbox(self) -> None:
        for phase in ("plan", "review"):
            self.executor().run(
                phase=phase,
                prompt=f"{phase} the app",
                workspace=self.workspace,
                schema=SCHEMA,
                log_dir=self.log_dir,
            )
            args = json.loads((self.root / "args.json").read_text(encoding="utf-8"))
            self.assertEqual(args[args.index("--sandbox") + 1], "read-only")

    def test_nonzero_exit_rejects_valid_looking_output(self) -> None:
        self.mode_file.write_text("nonzero", encoding="utf-8")

        with self.assertRaisesRegex(ExecutorError, "exited unsuccessfully"):
            self.executor().run(
                phase="build",
                prompt="Do the work",
                workspace=self.workspace,
                schema=SCHEMA,
                log_dir=self.log_dir,
            )

        invocation = self.invocations()[0]
        self.assertEqual(json.loads((invocation / "result.json").read_text()), {"ok": True})
        self.assertEqual((invocation / "stderr.log").read_text().strip(), "fake stderr")

    def test_does_not_reuse_a_previous_result(self) -> None:
        invocations_before_first = set(self.invocations())
        self.executor().run(
            phase="build",
            prompt="First run",
            workspace=self.workspace,
            schema=SCHEMA,
            log_dir=self.log_dir,
        )
        first_invocations = set(self.invocations()) - invocations_before_first
        self.assertEqual(len(first_invocations), 1)
        first_invocation = first_invocations.pop()
        self.mode_file.write_text("none", encoding="utf-8")

        invocations_before_second = set(self.invocations())
        with self.assertRaisesRegex(ExecutorError, "did not produce a result"):
            self.executor().run(
                phase="build",
                prompt="Second run",
                workspace=self.workspace,
                schema=SCHEMA,
                log_dir=self.log_dir,
            )

        second_invocations = set(self.invocations()) - invocations_before_second
        self.assertEqual(len(second_invocations), 1)
        second_invocation = second_invocations.pop()
        self.assertEqual(len(self.invocations()), 2)
        self.assertNotEqual(first_invocation, second_invocation)
        self.assertTrue((first_invocation / "result.json").is_file())
        self.assertFalse((second_invocation / "result.json").exists())

    def test_invalid_schema_is_rejected_without_starting_cli(self) -> None:
        with self.assertRaisesRegex(ExecutorError, "schema is invalid"):
            self.executor().run(
                phase="plan",
                prompt="Plan the work",
                workspace=self.workspace,
                schema={"type": "not-a-json-schema-type"},
                log_dir=self.log_dir,
            )

        self.assertFalse((self.root / "args.json").exists())

    def test_response_that_violates_schema_is_rejected(self) -> None:
        self.mode_file.write_text("invalid_response", encoding="utf-8")

        with self.assertRaisesRegex(ExecutorError, "did not match the schema"):
            self.executor().run(
                phase="review",
                prompt="Review the work",
                workspace=self.workspace,
                schema=SCHEMA,
                log_dir=self.log_dir,
            )

    @unittest.skipUnless(os.name == "posix", "process-group cleanup is POSIX-specific")
    def test_timeout_kills_child_processes(self) -> None:
        self.mode_file.write_text("timeout", encoding="utf-8")
        owned_processes: list[subprocess.Popen[bytes]] = []
        real_popen = subprocess.Popen

        def ready_popen(*popen_args, **popen_kwargs):
            if (
                not popen_args
                or not popen_args[0]
                or Path(popen_args[0][0]) != self.fake_codex
            ):
                self.fail(
                    "timeout fixture setup failure: Popen argv[0] was not its fake CLI"
                )
            if popen_kwargs.get("start_new_session") is not True:
                self.fail(
                    "timeout fixture setup failure: fake CLI did not start a new session"
                )

            process = real_popen(*popen_args, **popen_kwargs)
            owned_processes.append(process)
            command = popen_args[0]
            result_path = Path(
                command[command.index("--output-last-message") + 1]
            )
            child_pid_path = self.root / "child.pid"
            marker = self.root / "alive.txt"
            deadline = time.monotonic() + 10
            previous_marker_size = None

            while time.monotonic() < deadline:
                if process.poll() is not None:
                    self.fail(
                        "timeout fixture setup failure: fake CLI exited before readiness"
                    )
                try:
                    result = json.loads(result_path.read_text(encoding="utf-8"))
                    child_pid = int(child_pid_path.read_text(encoding="utf-8"))
                    marker_size = marker.stat().st_size
                except (OSError, ValueError, json.JSONDecodeError):
                    time.sleep(0.02)
                    continue

                if (
                    result == {"ok": True}
                    and child_pid > 0
                    and previous_marker_size is not None
                    and marker_size > previous_marker_size
                ):
                    return process
                previous_marker_size = marker_size
                time.sleep(0.02)

            self.fail(
                "timeout fixture setup failure: fake CLI result, child PID, and "
                "advancing alive marker were not ready within 10 seconds"
            )

        try:
            with patch(
                "discovery_runtime.delivery_executor.subprocess.Popen",
                side_effect=ready_popen,
            ):
                with self.assertRaisesRegex(ExecutorError, "timed out"):
                    # Readiness is checked before the executor starts its real timeout.
                    self.executor(timeout=2).run(
                        phase="build",
                        prompt="Run a long build",
                        workspace=self.workspace,
                        schema=SCHEMA,
                        log_dir=self.log_dir,
                    )

            invocation = self.invocations()[0]
            self.assertEqual(
                json.loads((invocation / "result.json").read_text()), {"ok": True}
            )
            marker = self.root / "alive.txt"
            self.assertTrue(marker.exists())
            first_size = marker.stat().st_size
            time.sleep(0.15)
            self.assertEqual(marker.stat().st_size, first_size)
        finally:
            for process in owned_processes:
                cleanup_failure = None
                try:
                    os.killpg(process.pid, 0)
                except ProcessLookupError:
                    pass
                except OSError as exc:
                    cleanup_failure = (
                        "timeout fixture cleanup failure: could not probe owned "
                        f"process group ({exc})"
                    )
                    try:
                        CodexExecutor._terminate_process_tree(process)
                    except OSError as cleanup_exc:
                        cleanup_failure += f"; cleanup failed ({cleanup_exc})"
                else:
                    try:
                        CodexExecutor._terminate_process_tree(process)
                    except OSError as exc:
                        cleanup_failure = (
                            "timeout fixture cleanup failure: could not terminate "
                            f"owned process group ({exc})"
                        )

                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.fail(
                        "timeout fixture cleanup failure: saved fake CLI Popen "
                        "did not exit after owned-group cleanup"
                    )
                if cleanup_failure is not None:
                    self.fail(cleanup_failure)


if __name__ == "__main__":
    unittest.main()
