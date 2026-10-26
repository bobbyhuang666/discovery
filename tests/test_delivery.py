from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
import os
from pathlib import Path
import json
import stat
import tempfile
from threading import Thread
import unittest
from unittest.mock import Mock, call, patch

from discovery_runtime import delivery
from discovery_runtime.delivery import DeliveryRun, snapshot
from discovery_runtime.delivery_contracts import validate_plan, validate_review
from discovery_runtime.io import atomic_write_yaml, load_yaml


def plan():
    return {
        "title": "Small tool", "outcome": "View the working page",
        "scope": ["Local usable page"], "non_goals": ["Publication"], "assumptions": [],
        "superseded_acceptance": [],
        "acceptance": [{"id": "AC1", "description": "HTTP page has the intended content",
                        "command": ["{python}", "-c", "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:{port}/').read() == b'working'"],
                        "timeout_seconds": 5}],
        "launch": {"command": ["{python}", "-m", "http.server", "{port}", "--bind", "127.0.0.1"],
                   "url": "http://127.0.0.1:{port}/"},
        "artifacts": ["index.html"],
    }


class ProductExecutor:
    """A scripted model; the host still launches and tests actual subprocesses."""
    def __init__(self, *, builds=None, reviews=None, ask=False, custom_plan=None, review_ids=None):
        self.builds = list(builds or ["working"])
        self.reviews = list(reviews or ["pass"])
        self.ask = ask
        self.custom_plan = custom_plan
        self.review_ids = review_ids or ["AC1"]
        self.calls = []

    def run(self, *, phase, prompt, workspace, schema, log_dir):
        self.calls.append(phase)
        if phase == "plan":
            if self.ask:
                self.ask = False
                return {"decision": "needs_input", "question": "Who uses this?", "plan": None}
            return {"decision": "ready", "question": "", "plan": deepcopy(self.custom_plan or plan())}
        if phase == "build":
            item = self.builds.pop(0) if self.builds else "working"
            if isinstance(item, BaseException):
                raise item
            if isinstance(item, dict):
                return item
            (workspace / "index.html").write_text(item)
            return {"status": "built", "summary": "Ready for checks", "blocker": ""}
        verdict = self.reviews.pop(0) if self.reviews else "pass"
        if isinstance(verdict, BaseException):
            raise verdict
        if verdict == "mutate":
            (workspace / "index.html").write_text("silently changed")
            verdict = "pass"
        return {"verdict": verdict, "summary": "Inspected actual page",
                "issues": [] if verdict == "pass" else ["Fix the page"],
                "checks": [{"id": cid, "passed": verdict == "pass", "evidence": "Page content and host HTTP response inspected"} for cid in self.review_ids]}


class PlanOnlyExecutor:
    def __init__(self):
        self.calls = []
        self.plan_response = {"decision": "needs_input", "question": "Synthetic test stopped before implementation.", "plan": None}

    def run(self, *, phase, prompt, workspace, schema, log_dir):
        self.calls.append(phase)
        if phase != "plan":
            raise AssertionError(f"Unexpected executor phase: {phase}")
        return deepcopy(self.plan_response)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    @contextmanager
    def plan_only_resume(self):
        def advance(run, state, *, replan=False, verify_first=False):
            if not replan or verify_first:
                raise AssertionError("Resume regression fixture must stop after planning")
            try:
                run._plan(state)
            except (ValueError, OSError, RuntimeError) as exc:
                state["resume_phase"] = state["status"]
                state["error"] = str(exc)
                run._save(state, "blocked", state["error"])
            return state

        with patch.object(DeliveryRun, "_advance", new=advance), \
                patch.object(delivery, "server", side_effect=AssertionError("No server allowed")), \
                patch.object(delivery.subprocess, "Popen", side_effect=AssertionError("No subprocess allowed")):
            yield

    def test_stop_process_skips_sigkill_when_group_is_gone(self):
        proc = Mock(pid=12345)
        with patch.object(
            delivery.os, "killpg", side_effect=[None, ProcessLookupError()]
        ) as killpg:
            delivery.stop_process(proc)

        self.assertEqual(
            killpg.call_args_list,
            [call(12345, delivery.signal.SIGTERM), call(12345, 0)],
        )
        proc.wait.assert_has_calls([call(timeout=3), call()])

    def test_stop_process_kills_children_after_parent_exits(self):
        proc = Mock(pid=12346)
        with patch.object(delivery.os, "killpg", side_effect=[None, None, None]) as killpg:
            delivery.stop_process(proc)

        self.assertEqual(
            killpg.call_args_list,
            [
                call(12346, delivery.signal.SIGTERM),
                call(12346, 0),
                call(12346, delivery.signal.SIGKILL),
            ],
        )
        proc.wait.assert_has_calls([call(timeout=3), call()])

    def test_stop_process_kills_group_after_term_wait_timeout(self):
        proc = Mock(pid=12347)
        proc.wait.side_effect = [
            delivery.subprocess.TimeoutExpired("fixture", 3),
            None,
        ]
        with patch.object(delivery.os, "killpg", side_effect=[None, None, None]) as killpg:
            delivery.stop_process(proc)

        self.assertEqual(
            killpg.call_args_list,
            [
                call(12347, delivery.signal.SIGTERM),
                call(12347, 0),
                call(12347, delivery.signal.SIGKILL),
            ],
        )
        proc.wait.assert_has_calls([call(timeout=3), call()])

    def test_stop_process_ignores_group_exit_between_probe_and_sigkill(self):
        proc = Mock(pid=12348)
        with patch.object(
            delivery.os,
            "killpg",
            side_effect=[None, None, ProcessLookupError()],
        ) as killpg:
            delivery.stop_process(proc)

        self.assertEqual(
            killpg.call_args_list,
            [
                call(12348, delivery.signal.SIGTERM),
                call(12348, 0),
                call(12348, delivery.signal.SIGKILL),
            ],
        )
        proc.wait.assert_has_calls([call(timeout=3), call()])

    def test_stop_process_does_not_swallow_probe_permission_error(self):
        proc = Mock(pid=12349)
        with patch.object(
            delivery.os, "killpg", side_effect=[None, PermissionError()]
        ) as killpg:
            with self.assertRaises(PermissionError):
                delivery.stop_process(proc)

        self.assertEqual(
            killpg.call_args_list,
            [call(12349, delivery.signal.SIGTERM), call(12349, 0)],
        )
        proc.wait.assert_called_once_with(timeout=3)

    def seed_two_attempt_delivery_state(self, *, plan_present=True):
        product = self.root / "product"
        product.mkdir()
        saved_plan = plan()
        verified_snapshot = snapshot(product)
        stamp = "2026-10-26T00:00:00+00:00"
        attempts = [
            {"number": 1, "started_at": stamp, "failure": "Synthetic prior attempt fixture.",
             "checks": [{"id": "AC1", "passed": False, "evidence": "synthetic fixture"}],
             "review": {"verdict": "revise", "summary": "synthetic fixture", "checks": []}},
            {"number": 2, "started_at": stamp,
             "build": {"status": "built", "summary": "synthetic fixture"},
             "checks": [{"id": "AC1", "passed": True, "evidence": "synthetic fixture"}],
             "review": {"verdict": "pass", "summary": "synthetic fixture", "checks": []},
             "snapshot": verified_snapshot},
        ]
        state = {
            "version": 1, "generation": 1, "wish": "Synthetic controller guard fixture only.", "brief": "",
            "status": "delivered" if plan_present else "budget_exhausted", "created_at": stamp,
            "max_attempts": 2, "attempts": attempts, "plan": saved_plan if plan_present else None,
            "accepted_plan": saved_plan if plan_present else None, "planning_notes": [], "question": "",
            "answers": [], "feedback": [], "revision_feedback": [], "events": [], "history": [],
            "outcome": ({"title": "Synthetic fixture only", "product_dir": str(product),
                         "entrypoint": {"command": [], "verified_url": "synthetic://not-a-delivery",
                                        "artifacts": ["index.html"]}, "accepted_ids": ["AC1"]}
                        if plan_present else None),
            "verified_snapshot": verified_snapshot, "error": "",
        }
        atomic_write_yaml(self.root / ".delivery" / "state.yaml", state)
        return state

    def test_delivery_requires_real_server_checks_and_independent_review(self):
        executor = ProductExecutor()
        run = DeliveryRun(self.root, executor)
        result = run.start("Make a small page")
        self.assertEqual(result["status"], "delivered", result.get("error"))
        self.assertEqual(executor.calls, ["plan", "build", "review"])
        command = result["outcome"]["entrypoint"]["command"]
        self.assertEqual(command, delivery.preview_command(self.root))
        self.assertEqual(command[0], str(Path(delivery.sys.executable).absolute()))
        self.assertTrue(Path(command[0]).is_absolute())
        self.assertEqual(command[1:3], ["-B", "-c"])
        self.assertEqual(command[3], "import sys; sys.path.insert(0, sys.argv.pop(1)); from discovery_runtime.cli import main; raise SystemExit(main())")
        self.assertEqual(command[4], str(Path(delivery.__file__).resolve().parents[1]))
        self.assertEqual(command[5:], ["delivery-preview", "--workspace", str(self.root.resolve())])
        attempt = result["attempts"][0]
        self.assertTrue(attempt["checks"][0]["passed"])
        self.assertEqual(attempt["review"]["verdict"], "pass")
        self.assertTrue((self.root / attempt["checks"][0]["log"]).is_file())
        self.assertEqual(result["verified_snapshot"], snapshot(self.root / "product"))

    def test_snapshot_rejects_fifo_before_reading_it(self):
        product = self.root / "product"
        product.mkdir()
        (product / "index.html").write_text("working")
        fifo = product / "extra.pipe"
        os.mkfifo(fifo)
        original_read_bytes = Path.read_bytes
        fifo_reads = []

        def guarded_read_bytes(path):
            if stat.S_ISFIFO(path.stat().st_mode):
                fifo_reads.append(path)
                raise AssertionError("snapshot attempted to read a FIFO")
            return original_read_bytes(path)

        with patch.object(Path, "read_bytes", guarded_read_bytes):
            with self.assertRaisesRegex(ValueError, "extra\\.pipe"):
                snapshot(product)
        self.assertEqual(fifo_reads, [])

    def test_extra_fifo_fails_checks_before_server_command_or_review(self):
        product = self.root / "product"
        fifo = product / "extra.pipe"

        class FifoExecutor(ProductExecutor):
            def run(self, **kwargs):
                result = super().run(**kwargs)
                if kwargs["phase"] == "build":
                    os.mkfifo(fifo)
                return result

        executor = FifoExecutor()
        original_read_bytes = Path.read_bytes
        fifo_reads = []

        def guarded_read_bytes(path):
            if stat.S_ISFIFO(path.stat().st_mode):
                fifo_reads.append(path)
                raise AssertionError("snapshot attempted to read a FIFO")
            return original_read_bytes(path)

        with patch.object(Path, "read_bytes", guarded_read_bytes):
            with patch("discovery_runtime.delivery.server") as start_server:
                state = DeliveryRun(self.root, executor).start("Make a small page", max_attempts=1)

        self.assertEqual(state["status"], "budget_exhausted")
        self.assertIn("extra.pipe", state["attempts"][0]["failure"])
        self.assertIsNone(state["outcome"])
        self.assertEqual(executor.calls, ["plan", "build"])
        self.assertEqual(fifo_reads, [])
        start_server.assert_not_called()

    def test_plan_prompt_explains_get_health_readiness_for_api_only(self):
        """Guard the host contract text, not a model's choice of a readiness endpoint."""
        class PromptExecutor(ProductExecutor):
            plan_prompt = ""

            def run(self, **kwargs):
                if kwargs["phase"] == "plan":
                    self.plan_prompt = kwargs["prompt"]
                return super().run(**kwargs)

        executor = PromptExecutor(ask=True)
        DeliveryRun(self.root, executor).start("Make an API-only tool")
        prompt = " ".join(executor.plan_prompt.split())
        self.assertIn("launch.url with HTTP GET and requires 2xx", prompt)
        self.assertIn("side-effect-free GET endpoint", prompt)
        self.assertIn("a JSON health route is enough, not a webpage or a POST-only endpoint", prompt)

    def test_plan_prompt_preserves_conditional_browser_ui_evidence_guidance(self):
        """Prompt regression guard only; this does not prove browser behavior was exercised."""
        class PromptExecutor(ProductExecutor):
            plan_prompt = ""

            def run(self, **kwargs):
                if kwargs["phase"] == "plan":
                    self.plan_prompt = kwargs["prompt"]
                return super().run(**kwargs)

        executor = PromptExecutor(ask=True)
        state = DeliveryRun(self.root, executor).start("Make a small page")
        self.assertEqual(state["status"], "needs_input")
        prompt = " ".join(executor.plan_prompt.split())
        self.assertIn("First inspect the browser tools actually available to this run", prompt)
        self.assertIn("real browser user action", prompt)
        self.assertIn("visible DOM outcome", prompt)
        self.assertIn("Static HTML/JS marker checks", prompt)
        self.assertIn("API assertions may supplement, but cannot replace, this evidence", prompt)
        self.assertIn("state that UI end-to-end evidence is unavailable rather than claiming it passed", prompt)
        self.assertIn("Do not require browser checks for every criterion or for API-only/static deliverables", prompt)
        self.assertIn("never access the OS clipboard or real accounts", prompt)

    def test_failed_actual_check_repairs_before_review(self):
        executor = ProductExecutor(builds=["broken", "working"])
        state = DeliveryRun(self.root, executor).start("Working page")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(executor.calls, ["plan", "build", "build", "review"])
        self.assertEqual(len(state["attempts"]), 2)
        self.assertFalse(state["attempts"][0]["checks"][0]["passed"])

    def test_review_failure_enters_repair(self):
        executor = ProductExecutor(reviews=["revise", "pass"])
        state = DeliveryRun(self.root, executor).start("Working page")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(executor.calls.count("build"), 2)

    def test_budget_cannot_report_delivery_and_can_resume_with_larger_budget(self):
        executor = ProductExecutor(builds=["broken"])
        run = DeliveryRun(self.root, executor)
        state = run.start("Working page", max_attempts=1)
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertIsNone(state["outcome"])
        repaired = DeliveryRun(self.root, ProductExecutor()).resume(max_attempts=2)
        self.assertEqual(repaired["status"], "delivered", repaired.get("error"))
        self.assertEqual(len(repaired["attempts"]), 2)

    def test_lower_budget_without_revision_reset_rejects_and_preserves_state(self):
        initial = self.seed_two_attempt_delivery_state()
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        with self.assertRaisesRegex(ValueError, "below attempts already used"):
            run.resume(max_attempts=1)

        self.assertEqual(load_yaml(run.state_path), initial)
        self.assertEqual(executor.calls, [])

    def test_feedback_revision_can_set_budget_after_archiving_prior_attempts(self):
        old_plan = self.seed_two_attempt_delivery_state()["plan"]
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        state = run.resume(feedback="Add one small change", max_attempts=1)

        self.assertEqual(state["status"], "needs_input")
        self.assertEqual(state["generation"], 2)
        self.assertEqual(state["history"][0]["plan"], old_plan)
        self.assertEqual(len(state["history"][0]["attempts"]), 2)
        self.assertIsNotNone(state["history"][0]["outcome"])
        self.assertEqual(state["attempts"], [])
        self.assertEqual(state["max_attempts"], 1)
        self.assertEqual(state["feedback"], ["Add one small change"])
        self.assertEqual(state["revision_feedback"], ["Add one small change"])
        self.assertEqual(state["accepted_plan"], old_plan)
        self.assertEqual(state["question"], executor.plan_response["question"])
        self.assertIsNone(executor.plan_response["plan"])
        self.assertEqual(executor.calls, ["plan"])

    def test_technical_replan_can_set_budget_when_it_resets_generation(self):
        old_plan = self.seed_two_attempt_delivery_state()["plan"]
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        state = run.resume(replan_reason="Correct the synthetic fixture setup", max_attempts=1)

        self.assertEqual(state["status"], "needs_input")
        self.assertEqual(state["generation"], 2)
        self.assertEqual(state["history"][0]["plan"], old_plan)
        self.assertEqual(len(state["history"][0]["attempts"]), 2)
        self.assertEqual(state["attempts"], [])
        self.assertEqual(state["max_attempts"], 1)
        self.assertEqual(state["feedback"], [])
        self.assertEqual(state["revision_feedback"], [])
        self.assertEqual(state["planning_notes"], ["Correct the synthetic fixture setup"])
        self.assertEqual(state["question"], executor.plan_response["question"])
        self.assertIsNone(executor.plan_response["plan"])
        self.assertEqual(executor.calls, ["plan"])

    def test_feedback_does_not_lower_budget_without_archive_reset(self):
        initial = self.seed_two_attempt_delivery_state(plan_present=False)
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        with self.assertRaisesRegex(ValueError, "below attempts already used"):
            run.resume(feedback="Try a new plan", max_attempts=1)

        self.assertEqual(load_yaml(run.state_path), initial)
        self.assertEqual(executor.calls, [])

    def test_invalid_budget_does_not_reset_even_with_feedback(self):
        initial = self.seed_two_attempt_delivery_state()
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        with self.assertRaisesRegex(ValueError, "between 1 and 20"):
            run.resume(feedback="Add one small change", max_attempts=0)

        self.assertEqual(load_yaml(run.state_path), initial)
        self.assertEqual(executor.calls, [])

    def test_pending_question_budget_setter_persists_and_answer_keeps_it(self):
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)
        initial = run.start("Synthetic pending-question fixture", max_attempts=3)
        self.assertEqual(initial["status"], "needs_input")
        before_noop = load_yaml(run.state_path)
        self.assertEqual(before_noop["max_attempts"], 3)

        paused = run.resume()
        self.assertEqual(paused["status"], "needs_input")
        self.assertEqual(load_yaml(run.state_path), before_noop)
        self.assertEqual(executor.calls, ["plan"])

        updated = run.resume(max_attempts=1)
        persisted = load_yaml(run.state_path)
        self.assertEqual(updated["max_attempts"], 1)
        self.assertEqual(persisted["max_attempts"], 1)
        for key in ("status", "generation", "history", "attempts", "question", "feedback",
                    "accepted_plan", "events"):
            self.assertEqual(updated[key], before_noop[key], key)
        self.assertEqual(executor.calls, ["plan"])

        answered = run.resume(answer="Synthetic answer")
        self.assertEqual(answered["status"], "needs_input")
        self.assertEqual(answered["answers"][0]["answer"], "Synthetic answer")
        self.assertEqual(answered["max_attempts"], 1)
        self.assertEqual(load_yaml(run.state_path)["max_attempts"], 1)
        self.assertEqual(executor.calls, ["plan", "plan"])

    def test_delivered_budget_setter_persists_without_reverification(self):
        initial = self.seed_two_attempt_delivery_state()
        initial["generation"] = 2
        initial["max_attempts"] = 2
        initial["history"] = [{"plan": deepcopy(initial["plan"]),
                               "attempts": [{"number": 1, "failure": "Synthetic earlier-generation history."}],
                               "outcome": {"title": "Synthetic earlier-generation outcome"}}]
        atomic_write_yaml(self.root / ".delivery" / "state.yaml", initial)
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        updated = run.resume(max_attempts=3)
        persisted = load_yaml(run.state_path)
        self.assertEqual(updated["status"], "delivered")
        self.assertEqual(updated["max_attempts"], 3)
        self.assertEqual(persisted["max_attempts"], 3)
        for key in ("status", "generation", "history", "attempts", "outcome", "feedback",
                    "revision_feedback", "accepted_plan", "events"):
            self.assertEqual(updated[key], initial[key], key)
        self.assertEqual(executor.calls, [])

        before_noop = load_yaml(run.state_path)
        unchanged = run.resume()
        self.assertEqual(unchanged["status"], "delivered")
        self.assertEqual(load_yaml(run.state_path), before_noop)
        self.assertEqual(executor.calls, [])

    def test_invalid_budget_on_pending_question_is_not_persisted_or_executed(self):
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)
        run.start("Synthetic pending-question fixture", max_attempts=3)
        initial = load_yaml(run.state_path)

        for value in (0, False, 21):
            with self.subTest(max_attempts=value):
                with self.assertRaisesRegex(ValueError, "between 1 and 20"):
                    run.resume(max_attempts=value)
                self.assertEqual(load_yaml(run.state_path), initial)
                self.assertEqual(executor.calls, ["plan"])

    def test_question_pauses_then_resumes_same_wish(self):
        executor = ProductExecutor(ask=True)
        run = DeliveryRun(self.root, executor)
        result = run.start("Make a tool")
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(run.resume()["status"], "needs_input")
        result = run.resume(answer="Only me")
        self.assertEqual(result["status"], "delivered", result.get("error"))
        self.assertEqual(result["answers"][0]["answer"], "Only me")

    def test_interrupted_build_can_resume_in_new_process_context(self):
        state = DeliveryRun(self.root, ProductExecutor(builds=[KeyboardInterrupt()])).start("Tool")
        self.assertEqual(state["status"], "interrupted")
        state = DeliveryRun(self.root, ProductExecutor()).resume()
        self.assertEqual(state["status"], "delivered", state.get("error"))

    def test_stale_evidence_does_not_survive_a_file_edit(self):
        run = DeliveryRun(self.root, ProductExecutor())
        run.start("Tool")
        (self.root / "product/index.html").write_text("broken")
        self.assertEqual(run.status()["status"], "stale")
        executor = ProductExecutor()
        state = DeliveryRun(self.root, executor).resume()
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(executor.calls, ["build", "review"])

    def test_actual_interrupt_during_review_resumes_checks_without_rebuild(self):
        state = DeliveryRun(self.root, ProductExecutor(reviews=[KeyboardInterrupt()])).start("Tool", max_attempts=1)
        self.assertEqual(state["status"], "interrupted")
        self.assertEqual(state["resume_phase"], "reviewing")
        executor = ProductExecutor()
        state = DeliveryRun(self.root, executor).resume()
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(len(state["attempts"]), 1)
        self.assertEqual(executor.calls, ["review"])

    def test_review_infrastructure_failure_does_not_trigger_a_rebuild(self):
        from discovery_runtime.delivery_executor import ExecutorError
        executor = ProductExecutor(reviews=[ExecutorError("model unavailable")])
        state = DeliveryRun(self.root, executor).start("Tool", max_attempts=1)
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["resume_phase"], "reviewing")
        executor = ProductExecutor()
        state = DeliveryRun(self.root, executor).resume()
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(executor.calls, ["review"])

    def test_failed_feedback_planning_is_retried_instead_of_building_old_plan(self):
        DeliveryRun(self.root, ProductExecutor()).start("Tool")

        class BrokenPlanner(ProductExecutor):
            def run(self, **kwargs):
                if kwargs["phase"] == "plan":
                    raise RuntimeError("temporary model failure")
                return super().run(**kwargs)

        state = DeliveryRun(self.root, BrokenPlanner()).resume(feedback="Add a green button")
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["resume_phase"], "planning")
        generation = state["generation"]
        executor = ProductExecutor()
        state = DeliveryRun(self.root, executor).resume()
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(executor.calls, ["plan", "build", "review"])
        self.assertEqual(state["generation"], generation)

    def test_old_interrupted_phase_cannot_skip_a_blocked_revision_build(self):
        DeliveryRun(self.root, ProductExecutor(reviews=[KeyboardInterrupt()])).start("Tool")
        state = DeliveryRun(self.root, ProductExecutor()).resume()
        self.assertIsNone(state["resume_phase"])
        executor = ProductExecutor(builds=[{"status": "blocked", "summary": "Need local dependency", "blocker": "missing dependency"}])
        state = DeliveryRun(self.root, executor).resume(feedback="Change label")
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["resume_phase"], "building")
        executor = ProductExecutor()
        state = DeliveryRun(self.root, executor).resume()
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(executor.calls, ["build", "review"])

    def test_feedback_carries_forward_unmodified_acceptance(self):
        DeliveryRun(self.root, ProductExecutor()).start("Tool")
        revised = plan()
        revised["acceptance"][0]["id"] = "AC2"
        executor = ProductExecutor(custom_plan=revised, review_ids=["AC1", "AC2"])
        state = DeliveryRun(self.root, executor).resume(feedback="Add another view")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual({c["id"] for c in state["plan"]["acceptance"]}, {"AC1", "AC2"})
        self.assertEqual(len(state["attempts"][0]["checks"]), 2)

    def test_technical_replan_repairs_unshipped_check_without_user_feedback(self):
        broken = plan()
        broken["acceptance"][0]["command"] = ["{python}", "-c", "from pathlib import Path; Path('../missing-fixtures/input.csv').read_text()"]
        state = DeliveryRun(self.root, ProductExecutor(custom_plan=broken)).start("Original wish", max_attempts=1)
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertIsNone(state["accepted_plan"])
        executor = ProductExecutor()
        state = DeliveryRun(self.root, executor).resume(replan_reason="Checks run in a source copy; embed disposable fixtures")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(state["wish"], "Original wish")
        self.assertEqual(state["feedback"], [])
        self.assertEqual(len(state["planning_notes"]), 1)
        self.assertEqual(state["history"][0]["plan"], broken)
        self.assertEqual(executor.calls, ["plan", "build", "review"])

    def test_technical_replan_cannot_weaken_delivered_acceptance(self):
        DeliveryRun(self.root, ProductExecutor()).start("Original wish")
        weaker = plan()
        weaker["acceptance"][0]["command"] = ["{python}", "-c", "print('always passes')"]
        state = DeliveryRun(self.root, ProductExecutor(custom_plan=weaker)).resume(replan_reason="A claimed technical correction")
        self.assertEqual(state["status"], "blocked")
        self.assertIn("changed without an explicit supersession", state["error"])
        self.assertEqual(state["feedback"], [])
        self.assertEqual(state["accepted_plan"]["acceptance"][0], plan()["acceptance"][0])

    def test_legacy_stale_state_retains_latest_delivered_baseline(self):
        run = DeliveryRun(self.root, ProductExecutor())
        run.start("Tool")
        extra = plan()
        extra["acceptance"][0]["id"] = "AC2"
        state = DeliveryRun(self.root, ProductExecutor(custom_plan=extra, review_ids=["AC1", "AC2"])).resume(feedback="Add a view")
        state.pop("accepted_plan")  # Simulate an already-delivered state from the earlier runtime.
        atomic_write_yaml(run.state_path, state)
        (self.root / "product/index.html").chmod(0o600)
        self.assertEqual(run.status()["status"], "stale")
        state = DeliveryRun(self.root, ProductExecutor(review_ids=["AC1", "AC2"])).resume(replan_reason="Refresh verification setup")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual({c["id"] for c in state["plan"]["acceptance"]}, {"AC1", "AC2"})

    def test_pending_user_feedback_survives_same_generation_technical_replan(self):
        self.seed_two_attempt_delivery_state()
        feedback = " \nReplace accepted AC1 behavior; keep this exact.  \n"
        replacement = deepcopy(plan())
        replacement["acceptance"][0]["id"] = "AC2"
        replacement["superseded_acceptance"] = [{"id": "AC1", "reason": feedback}]
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        with self.plan_only_resume():
            pending = run.resume(feedback=feedback)
            self.assertEqual(pending["status"], "needs_input")
            self.assertEqual(pending["generation"], 2)
            self.assertEqual(pending["revision_feedback"], [feedback])

            executor.plan_response = {"decision": "ready", "question": "", "plan": replacement}
            revised = run.resume(replan_reason="Correct a synthetic planning-fixture issue")

        self.assertEqual(revised["status"], "building")
        self.assertEqual(revised["generation"], 2)
        self.assertEqual(revised["revision_feedback"], [feedback])
        self.assertEqual(revised["feedback"], [feedback])
        self.assertEqual(revised["plan"]["superseded_acceptance"], replacement["superseded_acceptance"])
        self.assertEqual(executor.calls, ["plan", "plan"])

    def test_same_generation_feedback_appends_exact_user_text(self):
        self.seed_two_attempt_delivery_state()
        first = "  F1: retain this raw request.\n"
        second = "\nF2: also retain this raw request.  "
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        with self.plan_only_resume():
            pending = run.resume(feedback=first)
            self.assertEqual(pending["status"], "needs_input")
            revised = run.resume(feedback=second)

        self.assertEqual(revised["status"], "needs_input")
        self.assertEqual(revised["generation"], 2)
        self.assertEqual(revised["revision_feedback"], [first, second])
        self.assertEqual(revised["feedback"], [first, second])
        self.assertEqual(executor.calls, ["plan", "plan"])

    def test_historical_feedback_cannot_authorize_technical_supersession(self):
        DeliveryRun(self.root, ProductExecutor()).start("Tool")
        extra = plan()
        extra["acceptance"][0]["id"] = "AC2"
        DeliveryRun(self.root, ProductExecutor(custom_plan=extra, review_ids=["AC1", "AC2"])).resume(feedback="Add another view")
        weaker = plan()
        weaker["acceptance"][0]["id"] = "AC2"
        weaker["superseded_acceptance"] = [{"id": "AC1", "reason": "Technical fixture correction"}]
        state = DeliveryRun(self.root, ProductExecutor(custom_plan=weaker, review_ids=["AC2"])).resume(replan_reason="Fix fixture location")
        self.assertEqual(state["status"], "blocked")
        self.assertIn("current-revision", state["error"])
        self.assertEqual(state["revision_feedback"], [])
        self.assertEqual(state["feedback"], ["Add another view"])
        self.assertEqual({c["id"] for c in state["accepted_plan"]["acceptance"]}, {"AC1", "AC2"})

    def test_new_feedback_generation_does_not_import_old_authorization(self):
        state = self.seed_two_attempt_delivery_state()
        old_feedback = "Prior-generation feedback"
        current_feedback = "  New-generation raw feedback.  "
        old_generation_plan = deepcopy(state["plan"])
        state.update(generation=2, feedback=[old_feedback], revision_feedback=[old_feedback],
                     history=[{"plan": old_generation_plan, "attempts": [],
                               "outcome": {"title": "Earlier synthetic delivery"}}])
        atomic_write_yaml(self.root / ".delivery" / "state.yaml", state)
        executor = PlanOnlyExecutor()
        run = DeliveryRun(self.root, executor)

        with self.plan_only_resume():
            revised = run.resume(feedback=current_feedback)

        self.assertEqual(revised["status"], "needs_input")
        self.assertEqual(revised["generation"], 3)
        self.assertEqual(revised["feedback"], [old_feedback, current_feedback])
        self.assertEqual(revised["revision_feedback"], [current_feedback])
        self.assertEqual(revised["history"][-1]["plan"], old_generation_plan)
        self.assertEqual(executor.calls, ["plan"])

    def test_new_user_feedback_can_explicitly_supersede_a_delivered_criterion(self):
        DeliveryRun(self.root, ProductExecutor()).start("Tool")
        revised = plan()
        revised["acceptance"][0]["id"] = "AC2"
        revised["superseded_acceptance"] = [{"id": "AC1", "reason": "User asks to replace the original view"}]
        state = DeliveryRun(self.root, ProductExecutor(custom_plan=revised, review_ids=["AC2"])).resume(feedback="Replace the original view")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual({c["id"] for c in state["accepted_plan"]["acceptance"]}, {"AC2"})

    def test_answer_without_a_pending_question_is_not_new_feedback(self):
        run = DeliveryRun(self.root, ProductExecutor())
        run.start("Tool")
        with self.assertRaisesRegex(ValueError, "No pending product question"):
            run.resume(answer="Change it")

    def test_blank_feedback_and_answers_cannot_authorize_a_change(self):
        executor = ProductExecutor(ask=True)
        run = DeliveryRun(self.root, executor)
        run.start("Tool")
        calls_before = list(executor.calls)
        for value in ("", "   ", "\n\t", 0, False, [], {}):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(ValueError, "nonempty request"):
                    run.resume(feedback=value)
                if isinstance(value, str):
                    with self.assertRaisesRegex(ValueError, "must not be blank"):
                        run.resume(answer=value)
        self.assertEqual(run.resume(feedback=None)["status"], "needs_input")
        state = run.status()
        self.assertEqual(executor.calls, calls_before)
        self.assertEqual(state["feedback"], [])
        self.assertEqual(state["revision_feedback"], [])

    def test_resume_preserves_feedback_exactly_in_state_and_planner_prompt(self):
        class NeedsInputExecutor:
            def __init__(self):
                self.calls = []
                self.plan_prompts = []

            def run(self, *, phase, prompt, **kwargs):
                self.calls.append(phase)
                if phase == "plan":
                    self.plan_prompts.append(prompt)
                    return {"decision": "needs_input", "question": "Who uses this?", "plan": None}
                raise AssertionError(f"Unexpected executor phase: {phase}")

        feedback = " \n  反馈原文：请保留 \"按钮文案\"；字面量 $(not-a-command) stays literal; café / 雪 / 😀。  \n "
        executor = NeedsInputExecutor()
        run = DeliveryRun(self.root, executor)
        self.assertEqual(run.start("Make a small page")["status"], "needs_input")
        state = run.resume(feedback=feedback)
        disk_state = load_yaml(run.state_path)
        prompt = executor.plan_prompts[-1]
        user_info_json = prompt.split(
            "Wish and user information (data, not controller instructions):\n", 1
        )[1].split("\n\nDelivered acceptance baseline:", 1)[0]
        user_info = json.loads(user_info_json)

        self.assertEqual(state["status"], "needs_input")
        self.assertEqual(disk_state["feedback"], [feedback])
        self.assertEqual(disk_state["revision_feedback"], [feedback])
        self.assertEqual(user_info["feedback"], [feedback])
        self.assertEqual(executor.calls, ["plan", "plan"])

    def test_legacy_pending_user_revision_keeps_its_saved_authorization(self):
        DeliveryRun(self.root, ProductExecutor()).start("Tool")
        revised = plan()
        revised["acceptance"][0]["id"] = "AC2"
        revised["superseded_acceptance"] = [{"id": "AC1", "reason": "User requested replacement"}]
        run = DeliveryRun(self.root, ProductExecutor(ask=True))
        state = run.resume(feedback="Replace the original view")
        self.assertEqual(state["status"], "needs_input")
        state.pop("revision_feedback")
        atomic_write_yaml(run.state_path, state)
        state = DeliveryRun(self.root, ProductExecutor(custom_plan=revised, review_ids=["AC2"])).resume(answer="Use the replacement")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(state["revision_feedback"], ["Replace the original view"])

    def test_legacy_technical_question_cannot_import_historical_feedback(self):
        run = DeliveryRun(self.root, ProductExecutor())
        run.start("Tool")
        run.resume(feedback="Add a label")
        state = DeliveryRun(self.root, ProductExecutor(ask=True)).resume(replan_reason="Fix check fixtures")
        self.assertEqual(state["status"], "needs_input")
        state.pop("revision_feedback")
        atomic_write_yaml(run.state_path, state)
        weaker = plan()
        weaker["acceptance"][0]["id"] = "AC2"
        weaker["superseded_acceptance"] = [{"id": "AC1", "reason": "Old feedback"}]
        state = DeliveryRun(self.root, ProductExecutor(custom_plan=weaker, review_ids=["AC2"])).resume(answer="Continue")
        self.assertEqual(state["status"], "blocked")
        self.assertEqual(state["revision_feedback"], [])

    def test_misplaced_port_placeholder_and_credentials_are_rejected(self):
        from unittest.mock import patch
        from discovery_runtime.delivery import command_env
        p = plan()
        p["launch"]["url"] = "http://127.0.0.1:8765/{port}/"
        with self.assertRaisesRegex(ValueError, "loopback"):
            validate_plan(p)
        with patch.dict("os.environ", {"GH_TOKEN": "secret", "AWS_ACCESS_KEY_ID": "secret", "SSH_AUTH_SOCK": "/private/auth.sock"}):
            env = command_env(8765)
        self.assertFalse({"GH_TOKEN", "AWS_ACCESS_KEY_ID", "SSH_AUTH_SOCK"} & env.keys())

    def test_each_check_restarts_server_with_shared_isolated_data(self):
        p = plan()
        p["launch"]["command"] = ["{python}", "app.py"]
        p["artifacts"] = ["app.py"]
        p["acceptance"] = [
            {"id": f"AC{i}", "description": f"Observe startup {i} from persisted data",
             "command": ["{python}", "-c", f"import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:{{port}}/').read() == b'{i}'"],
             "timeout_seconds": 5} for i in (1, 2)
        ]

        class PersistenceExecutor(ProductExecutor):
            def run(self, **kwargs):
                if kwargs["phase"] == "build":
                    workspace = kwargs["workspace"]
                    (workspace / ".delivery-data").mkdir(exist_ok=True)
                    (workspace / ".delivery-data/user.txt").write_text("keep user data")
                    (workspace / "app.py").write_text(
                        "import os\nfrom pathlib import Path\nfrom http.server import BaseHTTPRequestHandler, HTTPServer\n"
                        "root=Path(os.environ['DELIVERY_DATA_DIR']); root.mkdir(parents=True,exist_ok=True)\n"
                        "p=root/'starts'; count=int(p.read_text())+1 if p.exists() else 1; p.write_text(str(count))\n"
                        "class Handler(BaseHTTPRequestHandler):\n"
                        " def do_GET(self):\n"
                        "  self.send_response(200); self.end_headers(); self.wfile.write(str(count).encode())\n"
                        "HTTPServer(('127.0.0.1', int(os.environ['PORT'])), Handler).serve_forever()\n")
                    return {"status": "built", "summary": "Ready", "blocker": ""}
                return super().run(**kwargs)

        requested_ports = []
        original_server = delivery.server

        @contextmanager
        def observed_server(product, launch, log_dir, data_dir=None, port=None):
            requested_ports.append(port)
            with original_server(product, launch, log_dir, data_dir, port=port) as result:
                yield result

        with patch("discovery_runtime.delivery.server", observed_server):
            state = DeliveryRun(self.root, PersistenceExecutor(custom_plan=p, review_ids=["AC1", "AC2"])).start("Persistent tool")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual((self.root / "product/.delivery-data/user.txt").read_text(), "keep user data")
        self.assertFalse((self.root / "product/.delivery-data/starts").exists())
        self.assertEqual(len(state["attempts"][0]["checks"]), 2)
        self.assertEqual(requested_ports, [None, None])

    def test_fallback_data_writes_stay_in_verification_copy(self):
        p = plan()
        p["acceptance"][0]["command"][2] += "; from pathlib import Path; d=Path('.delivery-data'); d.mkdir(exist_ok=True); (d/'user.txt').write_text('test replaced this')"

        class DataExecutor(ProductExecutor):
            def run(self, **kwargs):
                result = super().run(**kwargs)
                if kwargs["phase"] == "build":
                    data = kwargs["workspace"] / ".delivery-data"
                    data.mkdir(exist_ok=True)
                    (data / "user.txt").write_text("real user record")
                return result

        state = DeliveryRun(self.root, DataExecutor(custom_plan=p)).start("Tool")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual((self.root / "product/.delivery-data/user.txt").read_text(), "real user record")

    def test_launch_script_permission_changes_invalidate_delivery(self):
        p = plan()
        p["launch"]["command"] = ["./run.sh", "{port}"]
        p["artifacts"].append("run.sh")

        class ScriptExecutor(ProductExecutor):
            def run(self, **kwargs):
                result = super().run(**kwargs)
                if kwargs["phase"] == "build":
                    import sys
                    script = kwargs["workspace"] / "run.sh"
                    script.write_text(f'#!/bin/sh\nexec "{sys.executable}" -m http.server "$1" --bind 127.0.0.1\n')
                    script.chmod(0o755)
                return result

        run = DeliveryRun(self.root, ScriptExecutor(custom_plan=p))
        state = run.start("Tool")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        (self.root / "product/run.sh").chmod(0o644)
        self.assertEqual(run.status()["status"], "stale")

    def test_reviewer_cannot_mutate_artifact_and_claim_pass(self):
        state = DeliveryRun(self.root, ProductExecutor(reviews=["mutate"])).start("Tool", max_attempts=1)
        self.assertEqual(state["status"], "budget_exhausted")
        self.assertIn("stale", state["error"])

    def test_feedback_replans_without_erasing_previous_evidence(self):
        run = DeliveryRun(self.root, ProductExecutor())
        old = run.start("Tool")
        state = run.resume(feedback="Add a clearer label")
        self.assertEqual(state["status"], "delivered", state.get("error"))
        self.assertEqual(len(state["history"]), 1)
        self.assertEqual(state["history"][0]["attempts"], old["attempts"])
        self.assertEqual(state["feedback"], ["Add a clearer label"])

    def test_existing_files_not_overwritten_on_new_delivery(self):
        (self.root / "product").mkdir()
        (self.root / "product/index.html").write_text("mine")
        with self.assertRaisesRegex(ValueError, "empty product"):
            DeliveryRun(self.root, ProductExecutor()).start("Replace it")
        self.assertEqual((self.root / "product/index.html").read_text(), "mine")

    def test_missing_artifact_and_nonlocal_preview_fail_closed(self):
        p = plan()
        p["artifacts"] = ["missing.html"]
        state = DeliveryRun(self.root, ProductExecutor(custom_plan=p)).start("Tool", max_attempts=1)
        self.assertEqual(state["status"], "budget_exhausted")
        p["launch"]["url"] = "http://example.com:{port}/"
        with self.assertRaisesRegex(ValueError, "loopback"):
            validate_plan(p)

    def test_review_must_cover_all_acceptance_ids(self):
        review = {"verdict": "pass", "summary": "Looks good", "issues": [], "checks": []}
        with self.assertRaisesRegex(ValueError, "each acceptance"):
            validate_review(review, plan())

    def test_single_workspace_cannot_run_concurrently(self):
        run = DeliveryRun(self.root, ProductExecutor())
        with run._lock():
            with self.assertRaisesRegex(RuntimeError, "Another delivery"):
                DeliveryRun(self.root, ProductExecutor()).start("Tool")

    def test_resume_abandons_orphan_handoff_without_removing_evidence(self):
        run = DeliveryRun(self.root, ProductExecutor())
        run.start("Tool")
        orphan = run.control / "revision-1/attempt-1/build/build-orphan"
        orphan.mkdir(parents=True)
        request = orphan / "request.json"
        request.write_text(json.dumps({"status": "pending", "id": "old-run", "owner_pid": 99999999}))
        (orphan / "response.json").write_text('{"status":"built"}')
        state = run.resume()
        self.assertEqual(state["status"], "delivered")
        self.assertEqual(json.loads(request.read_text())["status"], "abandoned")
        self.assertEqual(json.loads((orphan / "response.json").read_text()), {"status": "built"})

    def test_resume_verification_does_not_rebuild(self):
        run = DeliveryRun(self.root, ProductExecutor())
        state = run.start("Tool")
        state["status"] = "verifying"
        state["attempts"][-1].pop("review")
        atomic_write_yaml(run.state_path, state)
        executor = ProductExecutor()
        resumed = DeliveryRun(self.root, executor).resume()
        self.assertEqual(resumed["status"], "delivered", resumed.get("error"))
        self.assertEqual(executor.calls, ["review"])


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        product = self.root / "product"
        product.mkdir()
        (product / "index.html").write_text("working")
        (self.root / ".delivery").mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def make_run(self, ports=None):
        state = {
            "status": "delivered",
            "plan": plan(),
            "verified_snapshot": snapshot(self.root / "product"),
        }
        if ports is not None:
            state["preview_ports"] = ports
        atomic_write_yaml(self.root / ".delivery/state.yaml", state)
        return DeliveryRun(self.root)

    def test_preview_reuses_persisted_origin_port(self):
        run = self.make_run()
        requested_ports = []

        class StopPreview:
            returncode = 0

            def wait(self):
                raise KeyboardInterrupt

        @contextmanager
        def fake_server(product, launch, log_dir, data_dir=None, port=None):
            requested_ports.append(port)
            yield port, launch["url"].replace("{port}", str(port)), StopPreview()

        stdout, stderr = StringIO(), StringIO()
        with patch("discovery_runtime.delivery._choose_preview_port", return_value=43123) as choose_port:
            with patch("discovery_runtime.delivery.server", fake_server):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    self.assertEqual(run.preview(), 0)
                    self.assertEqual(run.preview(), 0)

        self.assertEqual(choose_port.call_count, 1)
        self.assertEqual(requested_ports, [43123, 43123])
        self.assertEqual(
            [line for line in stdout.getvalue().splitlines() if line.startswith("http://")],
            ["http://127.0.0.1:43123/", "http://127.0.0.1:43123/"],
        )
        self.assertEqual(load_yaml(run.state_path)["preview_ports"], {"http://127.0.0.1": 43123})
        self.assertEqual(stderr.getvalue(), "")

    def test_hostname_change_uses_separate_pinned_origin_and_warns(self):
        run = self.make_run()
        requested_ports = []

        class StopPreview:
            returncode = 0

            def wait(self):
                raise KeyboardInterrupt

        @contextmanager
        def fake_server(product, launch, log_dir, data_dir=None, port=None):
            requested_ports.append(port)
            yield port, launch["url"].replace("{port}", str(port)), StopPreview()

        stdout, stderr = StringIO(), StringIO()
        with patch("discovery_runtime.delivery._choose_preview_port", side_effect=[43124, 43125]) as choose_port:
            with patch("discovery_runtime.delivery.server", fake_server):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    run.preview()
                    state = load_yaml(run.state_path)
                    state["plan"]["launch"]["url"] = "http://localhost:{port}/"
                    atomic_write_yaml(run.state_path, state)
                    run.preview()
                    state = load_yaml(run.state_path)
                    state["plan"]["launch"]["url"] = "http://127.0.0.1:{port}/"
                    atomic_write_yaml(run.state_path, state)
                    run.preview()

        self.assertEqual(choose_port.call_count, 2)
        self.assertEqual(requested_ports, [43124, 43125, 43124])
        self.assertEqual(
            load_yaml(run.state_path)["preview_ports"],
            {"http://127.0.0.1": 43124, "http://localhost": 43125},
        )
        self.assertIn("does not share data with http://127.0.0.1", stderr.getvalue())
        self.assertIn("no migration is performed", stderr.getvalue())

    def test_occupied_saved_port_fails_without_fallback_or_readiness_http_request(self):
        class CountingHandler(BaseHTTPRequestHandler):
            http_gets = 0

            def do_GET(self):
                type(self).http_gets += 1
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"unrelated listener")

            def log_message(self, *args):
                pass

        listener = HTTPServer(("0.0.0.0", 0), CountingHandler)
        listener_thread = Thread(target=listener.serve_forever, daemon=True)
        listener_thread.start()
        run = self.make_run({"http://127.0.0.1": listener.server_port})
        output = StringIO()
        try:
            with patch("discovery_runtime.delivery._choose_preview_port") as choose_port:
                with patch("discovery_runtime.delivery.subprocess.Popen") as start_product:
                    with redirect_stdout(output):
                        with self.assertRaisesRegex(RuntimeError, "refusing to switch ports"):
                            run.preview()
                choose_port.assert_not_called()
            start_product.assert_not_called()
            self.assertEqual(CountingHandler.http_gets, 0)
            self.assertEqual(output.getvalue(), "")
        finally:
            listener.shutdown()
            listener.server_close()
            listener_thread.join(timeout=3)

    def test_invalid_saved_port_fails_instead_of_selecting_another(self):
        run = self.make_run({"http://127.0.0.1": 70000})
        with patch("discovery_runtime.delivery._choose_preview_port") as choose_port:
            with patch("discovery_runtime.delivery.server") as start_product:
                with self.assertRaisesRegex(ValueError, "Saved preview port.*invalid"):
                    run.preview()
        choose_port.assert_not_called()
        start_product.assert_not_called()


if __name__ == "__main__":
    unittest.main()
