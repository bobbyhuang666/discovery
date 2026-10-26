from __future__ import annotations

import json
import shlex
import signal
import sys
import threading
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Callable


DELIVERY_EXIT_CODES = {
    "delivered": 0,
    "needs_input": 2,
    "blocked": 3,
    "budget_exhausted": 3,
    "interrupted": 3,
}


def _add_executor_args(parser: Any) -> None:
    parser.add_argument(
        "--executor", choices=["codex", "handoff"], default="codex",
        help="Use local Codex CLI or hand off model work to the host",
    )
    parser.add_argument("--model", default=None, help="Optional model override or handoff request")
    parser.add_argument("--reasoning-effort", default=None, help="Optional requested reasoning effort")
    parser.add_argument("--executor-timeout", type=int, default=900, help="Executor timeout in seconds")
    parser.add_argument("--codex-bin", default="codex", help="Codex executable (Codex executor only)")


def add_delivery_args(subparsers: Any) -> None:
    parser = subparsers.add_parser("deliver", help="Build, run, and verify a local website or tool")
    parser.add_argument("wish", help="What you want built")
    parser.add_argument("--workspace", required=True, help="Directory for delivery state and product files")
    parser.add_argument("--brief", help="Optional brief file to include as delivery context")
    parser.add_argument("--max-attempts", type=int, default=3)
    _add_executor_args(parser)
    parser.add_argument("--json", action="store_true", help="Print the structured result as JSON")

    parser = subparsers.add_parser("delivery-status", help="Show the current delivery status")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--json", action="store_true", help="Print the structured result as JSON")

    parser = subparsers.add_parser("delivery-resume", help="Continue a delivery with an answer or feedback")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--answer", help="Answer the current delivery question")
    parser.add_argument("--feedback", help="Feedback or requested changes to the delivered product")
    parser.add_argument("--replan-reason", help="Correct technical planning errors while preserving delivered behavior")
    parser.add_argument("--max-attempts", type=int, default=None)
    _add_executor_args(parser)
    parser.add_argument("--json", action="store_true", help="Print the structured result as JSON")

    parser = subparsers.add_parser("delivery-preview", help="Run the local product preview until Ctrl-C")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--json", action="store_true", help="Print the final structured preview result as JSON")


def _default_run_factory(args: Any, skill_root: Path | None) -> Any:
    from .delivery import DeliveryRun

    executor = None
    if args.cmd in {"deliver", "delivery-resume"}:
        if args.executor == "handoff":
            from .delivery_handoff import HandoffExecutor

            executor = HandoffExecutor(
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout=args.executor_timeout,
            )
        else:
            from .delivery_executor import CodexExecutor

            executor = CodexExecutor(
                executable=args.codex_bin,
                model=args.model,
                reasoning_effort=args.reasoning_effort,
                timeout=args.executor_timeout,
            )
    return DeliveryRun(Path(args.workspace), executor=executor, skill_root=skill_root)


def _status(result: dict[str, Any]) -> str:
    value = result.get("status")
    if value is None and isinstance(result.get("outcome"), dict):
        value = result["outcome"].get("status")
    if value is None and isinstance(result.get("outcome"), str):
        value = result["outcome"]
    return str(value or "interrupted").strip().lower().replace("-", "_").replace(" ", "_")


def _entrypoint(result: dict[str, Any]) -> dict[str, Any] | str | None:
    entrypoint = result.get("entrypoint")
    outcome = result.get("outcome")
    if entrypoint is None and isinstance(outcome, dict):
        entrypoint = outcome.get("entrypoint")
    return entrypoint


def _render_entrypoint(entrypoint: Any) -> Any:
    if not isinstance(entrypoint, dict):
        return entrypoint
    command = entrypoint.get("command")
    if (isinstance(command, list) and len(command) == 4
            and command[:3] == ["discovery", "delivery-preview", "--workspace"]
            and isinstance(command[3], str)):
        from .delivery import preview_command

        rendered = dict(entrypoint)
        rendered["command"] = preview_command(command[3])
        return rendered
    return entrypoint


def _render_result(result: dict[str, Any]) -> dict[str, Any]:
    rendered = dict(result)
    if "entrypoint" in rendered:
        rendered["entrypoint"] = _render_entrypoint(rendered["entrypoint"])
    outcome = rendered.get("outcome")
    if isinstance(outcome, dict) and "entrypoint" in outcome:
        rendered_outcome = dict(outcome)
        rendered_outcome["entrypoint"] = _render_entrypoint(rendered_outcome["entrypoint"])
        rendered["outcome"] = rendered_outcome
    return rendered


def _interrupt_preview_on_sigterm(signum: int, frame: Any) -> None:
    raise KeyboardInterrupt


def _print_result(result: dict[str, Any], *, as_json: bool) -> None:
    result = _render_result(result)
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return

    status = _status(result)
    print(f"Delivery: {status.replace('_', ' ')}")
    wish = result.get("wish")
    if isinstance(wish, str) and wish:
        print(f"Wish: {wish}")
    outcome = result.get("outcome")
    if isinstance(outcome, dict) and isinstance(outcome.get("title"), str):
        print(f"Product: {outcome['title']}")

    entrypoint = _entrypoint(result)
    if isinstance(entrypoint, dict):
        command = entrypoint.get("command")
        if isinstance(command, list) and command:
            print(f"Preview command: {shlex.join([str(part) for part in command])}")
        elif isinstance(entrypoint.get("path"), str):
            print(f"Entrypoint: {entrypoint['path']}")
        artifacts = entrypoint.get("artifacts")
        if isinstance(artifacts, list) and artifacts:
            print("Artifacts: " + ", ".join(str(path) for path in artifacts))
    elif isinstance(entrypoint, str) and entrypoint:
        print(f"Entrypoint: {entrypoint}")

    if status == "needs_input":
        question = result.get("question") or result.get("prompt")
        if question:
            print(f"Question: {question}")
    elif status == "delivered":
        print("The verified URL was used for local acceptance checks; it is not a running preview now.")

    errors = result.get("errors")
    if isinstance(errors, list):
        for error in errors:
            print(f"Error: {error}", file=sys.stderr)
    elif errors:
        print(f"Error: {errors}", file=sys.stderr)
    elif result.get("error"):
        print(f"Error: {result['error']}", file=sys.stderr)


def run_delivery_command(
    args: Any,
    *,
    skill_root: Path | None,
    run_factory: Callable[[Any, Path | None], Any] | None = None,
) -> int:
    try:
        run = (run_factory or _default_run_factory)(args, skill_root)
        if args.cmd == "deliver":
            brief = Path(args.brief).read_text(encoding="utf-8") if args.brief else None
            result = run.start(args.wish, max_attempts=args.max_attempts, brief=brief)
        elif args.cmd == "delivery-status":
            result = run.status()
        elif args.cmd == "delivery-resume":
            options = dict(answer=args.answer, feedback=args.feedback, max_attempts=args.max_attempts)
            if args.replan_reason is not None:
                options["replan_reason"] = args.replan_reason
            result = run.resume(**options)
        elif args.cmd == "delivery-preview":
            previous_sigterm_handler = None
            restore_sigterm_handler = False
            try:
                if threading.current_thread() is threading.main_thread():
                    previous_sigterm_handler = signal.getsignal(signal.SIGTERM)
                    restore_sigterm_handler = True
                    signal.signal(signal.SIGTERM, _interrupt_preview_on_sigterm)
                try:
                    if args.json:
                        with redirect_stdout(sys.stderr):
                            result = run.preview()
                    else:
                        result = run.preview()
                except KeyboardInterrupt:
                    if args.json:
                        print(json.dumps({"status": "stopped"}))
                    return 0
                preview_code = result if isinstance(result, int) and not isinstance(result, bool) else 0
                if args.json:
                    if isinstance(result, dict):
                        payload = result
                    elif preview_code == 0:
                        payload = {"status": "stopped"}
                    else:
                        payload = {"status": "failed", "return_code": preview_code}
                    _print_result(payload, as_json=True)
                elif isinstance(result, dict):
                    _print_result(result, as_json=False)
                if preview_code != 0:
                    print(f"Preview process exited with code {preview_code}.", file=sys.stderr)
                return preview_code
            finally:
                if restore_sigterm_handler:
                    signal.signal(signal.SIGTERM, previous_sigterm_handler)
        else:
            print(f"Error: unsupported delivery command: {args.cmd}", file=sys.stderr)
            return 1
        if not isinstance(result, dict):
            raise TypeError("DeliveryRun returned a non-object result")
        _print_result(result, as_json=args.json)
        return DELIVERY_EXIT_CODES.get(_status(result), 3)
    except KeyboardInterrupt:
        print("Delivery interrupted.", file=sys.stderr)
        return 3
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
