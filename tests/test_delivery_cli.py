from __future__ import annotations

import json
import os
import select
import shlex
import signal
import shutil
import socket
import subprocess
import tempfile
import time
import uuid
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from threading import Thread
from types import SimpleNamespace
from urllib.request import ProxyHandler, build_opener
from unittest.mock import Mock, patch

from discovery_runtime import cli, delivery, delivery_cli


def _process_group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def _wait_for_process_group_exit(pgid: int, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _process_group_exists(pgid):
            return True
        time.sleep(0.05)
    return not _process_group_exists(pgid)


def _cleanup_preview_fixture_group(pid: int, marker: str) -> None:
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    if pgid != pid:
        raise AssertionError(f"Refusing to signal fixture PID {pid}: PGID is {pgid}")
    identity = subprocess.run(
        ["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, check=False
    )
    if identity.returncode != 0 or marker not in identity.stdout:
        raise AssertionError(f"Refusing to signal fixture PID {pid}: process identity did not match")
    os.killpg(pgid, signal.SIGTERM)
    if not _wait_for_process_group_exit(pgid, 5):
        raise AssertionError(f"Fixture process group {pgid} remained after SIGTERM cleanup")


class DeliveryCliTests(unittest.TestCase):
    def test_deliver_routes_outside_skill_and_passes_brief_and_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            brief_path = workspace / "brief.md"
            brief_path.write_text("Use a calm blue palette.", encoding="utf-8")
            runner = Mock()
            runner.start.return_value = {"status": "needs_input", "question": "Which name?"}
            factory = Mock(return_value=runner)

            with patch.object(cli, "skill_root", side_effect=FileNotFoundError("skill is not installed here")):
                with patch.object(delivery_cli, "_default_run_factory", factory):
                    with redirect_stdout(StringIO()):
                        code = cli.main([
                            "deliver", "A habit tracker", "--workspace", str(workspace),
                            "--brief", str(brief_path), "--max-attempts", "2", "--model", "codex-mini",
                        ])

            factory.assert_called_once()
            args, root = factory.call_args.args
            self.assertEqual(args.cmd, "deliver")
            self.assertIsNone(root)
            runner.start.assert_called_once_with(
                "A habit tracker", max_attempts=2, brief="Use a calm blue palette."
            )
            self.assertEqual(code, 2)

    def test_status_routes_outside_skill_and_emits_json(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Mock()
            runner.status.return_value = {"status": "delivered", "wish": "A local tool"}
            with patch.object(cli, "skill_root", side_effect=FileNotFoundError("not installed")):
                with patch.object(delivery_cli, "_default_run_factory", return_value=runner):
                    output = StringIO()
                    with redirect_stdout(output):
                        code = cli.main([
                            "delivery-status", "--workspace", directory, "--json"
                        ])

            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue())["wish"], "A local tool")
            runner.status.assert_called_once_with()

    def test_handoff_selection_preserves_explicit_model_and_effort(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Mock()
            runner.start.return_value = {"status": "needs_input"}
            with patch("discovery_runtime.delivery_handoff.HandoffExecutor") as executor:
                with patch("discovery_runtime.delivery.DeliveryRun", return_value=runner) as run_class:
                    with redirect_stdout(StringIO()):
                        code = cli.main([
                            "deliver", "A small tool", "--workspace", directory,
                            "--executor", "handoff", "--model", "gpt-6-luna",
                            "--reasoning-effort", "high", "--executor-timeout", "17",
                        ])

            self.assertEqual(code, 2)
            executor.assert_called_once_with(
                model="gpt-6-luna", reasoning_effort="high", timeout=17
            )
            self.assertIs(run_class.call_args.kwargs["executor"], executor.return_value)

    def test_exit_codes_follow_delivery_status(self):
        expected = {
            "delivered": 0,
            "needs_input": 2,
            "blocked": 3,
            "budget_exhausted": 3,
            "interrupted": 3,
        }
        with tempfile.TemporaryDirectory() as directory:
            for status, code in expected.items():
                with self.subTest(status=status):
                    runner = Mock()
                    runner.status.return_value = {"status": status}
                    with patch.object(cli, "skill_root", side_effect=FileNotFoundError("not installed")):
                        with patch.object(delivery_cli, "_default_run_factory", return_value=runner):
                            with redirect_stdout(StringIO()):
                                actual = cli.main(["delivery-status", "--workspace", directory])
                    self.assertEqual(actual, code)

    def test_command_errors_return_one(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Mock()
            runner.start.side_effect = RuntimeError("Codex failed")
            with patch.object(delivery_cli, "_default_run_factory", return_value=runner):
                stderr = StringIO()
                with redirect_stderr(stderr):
                    code = cli.main(["deliver", "A tool", "--workspace", directory])

            self.assertEqual(code, 1)
            self.assertIn("Codex failed", stderr.getvalue())

    def test_resume_routes_technical_reason_separately_from_feedback(self):
        runner = Mock()
        runner.resume.return_value = {"status": "needs_input"}
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(delivery_cli, "_default_run_factory", return_value=runner):
                with redirect_stdout(StringIO()):
                    result = cli.main(["delivery-resume", "--workspace", directory,
                                       "--replan-reason", "Missing input fixtures"])
            self.assertEqual(result, 2)
            runner.resume.assert_called_once_with(answer=None, feedback=None, max_attempts=None,
                                                 replan_reason="Missing input fixtures")

    def test_preview_runs_without_executor_and_ctrl_c_is_success(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Mock()
            runner.preview.side_effect = KeyboardInterrupt
            factory = Mock(return_value=runner)
            with patch.object(cli, "skill_root", side_effect=FileNotFoundError("not installed")):
                with patch.object(delivery_cli, "_default_run_factory", factory):
                    with redirect_stdout(StringIO()):
                        code = cli.main(["delivery-preview", "--workspace", directory])

            self.assertEqual(code, 0)
            self.assertIsNone(factory.call_args.args[1])
            runner.preview.assert_called_once_with()

    def test_preview_json_keeps_live_url_off_json_stdout(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Mock()
            runner.preview.side_effect = lambda: print("http://127.0.0.1:5000")
            output = StringIO()
            live_output = StringIO()
            with patch.object(delivery_cli, "_default_run_factory", return_value=runner):
                with redirect_stdout(output), redirect_stderr(live_output):
                    code = cli.main([
                        "delivery-preview", "--workspace", directory, "--json"
                    ])

            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output.getvalue()), {"status": "stopped"})
            self.assertIn("http://127.0.0.1:5000", live_output.getvalue())

    def test_legacy_preview_entrypoint_is_adapted_only_in_human_and_json_output(self):
        workspace = "/tmp/legacy preview ; $literal's"
        legacy_command = ["discovery", "delivery-preview", "--workspace", workspace]
        result = {
            "status": "delivered",
            "outcome": {"entrypoint": {"command": legacy_command}},
        }
        expected = delivery.preview_command(workspace)

        human = StringIO()
        with redirect_stdout(human):
            delivery_cli._print_result(result, as_json=False)
        self.assertIn(f"Preview command: {shlex.join(expected)}", human.getvalue())
        self.assertEqual(result["outcome"]["entrypoint"]["command"], legacy_command)

        output = StringIO()
        with redirect_stdout(output):
            delivery_cli._print_result(result, as_json=True)
        self.assertEqual(
            json.loads(output.getvalue())["outcome"]["entrypoint"]["command"], expected
        )
        self.assertEqual(result["outcome"]["entrypoint"]["command"], legacy_command)

    def test_custom_preview_entrypoint_is_not_rewritten(self):
        custom = ["custom-runner", "delivery-preview", "--workspace", "/tmp/a workspace"]
        result = {"status": "delivered", "outcome": {"entrypoint": {"command": custom}}}
        human = StringIO()
        with redirect_stdout(human):
            delivery_cli._print_result(result, as_json=False)
        self.assertIn(f"Preview command: {shlex.join(custom)}", human.getvalue())

        output = StringIO()
        with redirect_stdout(output):
            delivery_cli._print_result(result, as_json=True)
        self.assertEqual(json.loads(output.getvalue())["outcome"]["entrypoint"]["command"], custom)
        self.assertEqual(result["outcome"]["entrypoint"]["command"], custom)

    def test_preview_propagates_nonzero_process_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            runner = Mock()
            runner.preview.return_value = 17
            output = StringIO()
            errors = StringIO()
            with patch.object(delivery_cli, "_default_run_factory", return_value=runner):
                with redirect_stdout(output), redirect_stderr(errors):
                    code = cli.main(["delivery-preview", "--workspace", directory])

            self.assertEqual(code, 17)
            self.assertIn("code 17", errors.getvalue())

    def test_preview_sigterm_handler_is_restored_for_all_outcomes_and_preview_only(self):
        previous_handler = signal.getsignal(signal.SIGTERM)
        scenarios = [
            ("success", None, 0),
            ("exception", RuntimeError("preview failed"), 1),
            ("keyboard interrupt", KeyboardInterrupt(), 0),
        ]
        with tempfile.TemporaryDirectory() as directory:
            for name, outcome, expected_code in scenarios:
                with self.subTest(outcome=name):
                    runner = Mock()
                    if isinstance(outcome, BaseException):
                        runner.preview.side_effect = outcome
                    else:
                        runner.preview.return_value = 0
                    with patch.object(delivery_cli.signal, "signal", wraps=signal.signal) as signal_spy:
                        with patch.object(cli, "skill_root", side_effect=FileNotFoundError("not installed")):
                            with patch.object(delivery_cli, "_default_run_factory", return_value=runner):
                                with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                                    code = cli.main([
                                        "delivery-preview", "--workspace", directory,
                                    ])

                    self.assertEqual(code, expected_code)
                    self.assertEqual(signal_spy.call_count, 2)
                    self.assertEqual(signal_spy.call_args_list[0].args[0], signal.SIGTERM)
                    self.assertIs(
                        signal_spy.call_args_list[0].args[1],
                        delivery_cli._interrupt_preview_on_sigterm,
                    )
                    self.assertEqual(signal_spy.call_args_list[1].args, (signal.SIGTERM, previous_handler))
                    self.assertEqual(signal.getsignal(signal.SIGTERM), previous_handler)

            runner = Mock()
            runner.status.return_value = {"status": "delivered"}
            with patch.object(delivery_cli.signal, "signal", wraps=signal.signal) as signal_spy:
                with patch.object(cli, "skill_root", side_effect=FileNotFoundError("not installed")):
                    with patch.object(delivery_cli, "_default_run_factory", return_value=runner):
                        with redirect_stdout(StringIO()):
                            code = cli.main(["delivery-status", "--workspace", directory])
            self.assertEqual(code, 0)
            signal_spy.assert_not_called()
            self.assertEqual(signal.getsignal(signal.SIGTERM), previous_handler)

            runner = Mock()
            runner.preview.return_value = 0
            results = []
            args = SimpleNamespace(cmd="delivery-preview", json=False)
            worker = Thread(target=lambda: results.append(
                delivery_cli.run_delivery_command(
                    args, skill_root=None, run_factory=lambda *_: runner,
                )
            ))
            with patch.object(delivery_cli.signal, "signal", wraps=signal.signal) as signal_spy:
                worker.start()
                worker.join(timeout=5)
            self.assertFalse(worker.is_alive(), "embedded preview call did not finish")
            self.assertEqual(results, [0])
            signal_spy.assert_not_called()

    def test_preview_sigterm_stops_cli_and_its_server_group(self):
        self._run_generated_preview_fixture(as_json=False)

    def test_preview_json_sigterm_stops_cli_and_keeps_url_off_stdout(self):
        self._run_generated_preview_fixture(as_json=True)

    def _run_generated_preview_fixture(self, *, as_json):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory) / "manual preview ; $literal's"
            workspace.mkdir()
            product = workspace / "product"
            control = workspace / ".delivery"
            product.mkdir()
            control.mkdir()
            (product / "index.html").write_text("temporary signal fixture", encoding="utf-8")
            marker = f"preview-sigterm-fixture-{uuid.uuid4().hex}"
            (product / "serve_fixture.py").write_text(
                "from http.server import BaseHTTPRequestHandler, HTTPServer\n"
                "import os, sys\n"
                "marker = sys.argv[3]\n"
                "assert marker.startswith('preview-sigterm-fixture-')\n"
                "open(sys.argv[2], 'w', encoding='utf-8').write(str(os.getpid()))\n"
                "class Handler(BaseHTTPRequestHandler):\n"
                "    def do_GET(self):\n"
                "        self.send_response(200)\n"
                "        self.end_headers()\n"
                "        self.wfile.write(b'fixture')\n"
                "    def log_message(self, *args):\n"
                "        pass\n"
                "HTTPServer(('127.0.0.1', int(sys.argv[1])), Handler).serve_forever()\n",
                encoding="utf-8",
            )
            pid_file = control / "fixture-server.pid"
            plan = {
                "title": "Temporary preview signal fixture",
                "outcome": "Serve a hand-authored loopback page",
                "scope": ["Temporary local test fixture"],
                "non_goals": ["No model work or acceptance run"],
                "assumptions": [],
                "superseded_acceptance": [],
                "acceptance": [{
                    "id": "fixture",
                    "description": "The temporary page responds locally",
                    "command": ["{python}", "-c", "pass"],
                    "timeout_seconds": 5,
                }],
                "launch": {
                    "command": [
                        "{python}", "-B", "serve_fixture.py", "{port}", str(pid_file), marker,
                    ],
                    "url": "http://127.0.0.1:{port}/",
                },
                "artifacts": ["index.html", "serve_fixture.py"],
            }
            (control / "state.yaml").write_text(
                json.dumps({"status": "stale", "plan": plan}), encoding="utf-8"
            )

            caller_cwd = Path(directory) / "empty caller cwd"
            caller_cwd.mkdir()
            empty_bin = Path(directory) / "empty bin"
            empty_bin.mkdir()
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            env["PATH"] = str(empty_bin)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            self.assertIsNone(shutil.which("discovery", path=env["PATH"]))
            argv = delivery.preview_command(workspace)
            if as_json:
                argv = argv + ["--json"]
            process = subprocess.Popen(
                argv,
                cwd=caller_cwd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            server_pid = None
            try:
                url_stream = process.stderr if as_json else process.stdout
                ready, _, _ = select.select([url_stream], [], [], 15)
                self.assertTrue(ready, "generated preview command did not print its loopback URL")
                url = url_stream.readline().strip()
                self.assertTrue(url.startswith("http://127.0.0.1:"), url)
                port = int(url.split(":", 2)[2].split("/", 1)[0])
                with build_opener(ProxyHandler({})).open(url, timeout=2) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.read(), b"fixture")
                server_pid = int(pid_file.read_text(encoding="utf-8"))

                process.send_signal(signal.SIGTERM)
                return_code = process.wait(timeout=10)
                self.assertEqual(return_code, 0, f"preview CLI exited with {return_code}")
                stdout_text = process.stdout.read()
                stderr_text = process.stderr.read()
                if as_json:
                    self.assertEqual(json.loads(stdout_text), {"status": "stopped"})
                    self.assertNotIn("http://127.0.0.1:", stdout_text)
                    live_output = url + stderr_text
                else:
                    live_output = url + stdout_text
                self.assertIn("Local preview running", live_output)
                self.assertTrue(
                    _wait_for_process_group_exit(server_pid, 5),
                    f"preview server process group {server_pid} remained after CLI exit",
                )
                with socket.socket() as sock:
                    sock.settimeout(1)
                    self.assertNotEqual(sock.connect_ex(("127.0.0.1", port)), 0)
                with socket.socket() as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.bind(("127.0.0.1", port))
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGTERM)
                    process.wait(timeout=10)
                if server_pid is None and pid_file.is_file():
                    server_pid = int(pid_file.read_text(encoding="utf-8"))
                if server_pid is not None and _process_group_exists(server_pid):
                    _cleanup_preview_fixture_group(server_pid, marker)
                process.stdout.close()
                process.stderr.close()


if __name__ == "__main__":
    unittest.main()
