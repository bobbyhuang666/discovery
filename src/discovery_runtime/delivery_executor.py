from __future__ import annotations

import json
import math
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validators
from jsonschema.exceptions import SchemaError


class ExecutorError(RuntimeError):
    """A safe, user-facing error from a Codex CLI invocation."""


class CodexExecutor:
    def __init__(
        self,
        executable: str = "codex",
        model: str | None = None,
        reasoning_effort: str | None = None,
        timeout: float = 900,
    ) -> None:
        if (
            not isinstance(timeout, (int, float))
            or isinstance(timeout, bool)
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise ValueError("timeout must be a finite number greater than zero")
        self.executable = executable
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
            raise ExecutorError("Codex executor received an unsupported phase")
        if not isinstance(prompt, str):
            raise ExecutorError("Codex executor prompt must be a string")
        if not isinstance(schema, dict):
            raise ExecutorError("Codex executor schema must be an object")

        try:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            invocation_dir = Path(
                tempfile.mkdtemp(prefix=f"{phase}-", dir=log_dir)
            )
            prompt_path = invocation_dir / "prompt.txt"
            schema_path = invocation_dir / "schema.json"
            result_path = invocation_dir / "result.json"
            stdout_path = invocation_dir / "stdout.log"
            stderr_path = invocation_dir / "stderr.log"

            prompt_path.write_text(prompt, encoding="utf-8")
            schema_path.write_text(
                json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            stdout_path.touch()
            stderr_path.touch()
        except (OSError, TypeError, ValueError):
            raise ExecutorError("Could not prepare Codex invocation logs") from None

        try:
            validator_class = validators.validator_for(schema)
            validator_class.check_schema(schema)
            response_validator = validator_class(schema)
        except (SchemaError, TypeError, ValueError):
            raise ExecutorError("Codex executor schema is invalid") from None

        sandbox = "workspace-write" if phase == "build" else "read-only"
        args = [
            self.executable,
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--color",
            "never",
            "--sandbox",
            sandbox,
            "-C",
            str(Path(workspace).resolve()),
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(result_path),
        ]
        if self.model is not None:
            args.extend(["-m", self.model])
        if self.reasoning_effort is not None:
            args.extend(
                [
                    "-c",
                    f"model_reasoning_effort={json.dumps(self.reasoning_effort)}",
                ]
            )
        args.append("-")

        try:
            with stdout_path.open("wb") as stdout_file, stderr_path.open(
                "wb"
            ) as stderr_file:
                process = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    shell=False,
                    start_new_session=(os.name == "posix"),
                )
                try:
                    process.communicate(input=prompt.encode("utf-8"), timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    self._terminate_process_tree(process)
                    process.communicate()
                    raise ExecutorError(
                        f"Codex CLI timed out after {self.timeout:g} seconds"
                    ) from None
                except KeyboardInterrupt:
                    self._terminate_process_tree(process)
                    try:
                        process.communicate()
                    except Exception:
                        pass
                    raise
        except ExecutorError:
            raise
        except KeyboardInterrupt:
            raise
        except OSError:
            raise ExecutorError("Codex CLI could not be started") from None

        if process.returncode != 0:
            raise ExecutorError("Codex CLI exited unsuccessfully")

        try:
            response = json.loads(result_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise ExecutorError("Codex CLI did not produce a result") from None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            raise ExecutorError("Codex CLI returned malformed JSON") from None

        if not isinstance(response, dict):
            raise ExecutorError("Codex CLI result must be a JSON object")
        try:
            response_validator.validate(response)
        except ValidationError:
            raise ExecutorError("Codex CLI result did not match the schema") from None
        return response

    @staticmethod
    def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            except OSError:
                try:
                    process.terminate()
                except OSError:
                    pass

            # Give well-behaved children a short chance to flush and exit, then
            # kill any remaining members of this invocation's process group.
            time.sleep(0.2)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError:
                try:
                    process.kill()
                except OSError:
                    pass
        else:
            try:
                process.terminate()
                process.wait(timeout=0.2)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    process.kill()
                except OSError:
                    pass

        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
