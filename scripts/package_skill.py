#!/usr/bin/env python3
"""Build and cold-validate a clean, isolated Discovery skill archive."""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


DEFAULT_OUTPUT_NAME = "discovery-v17.1.zip"
IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "site-packages",
    "build",
    "dist",
}
IGNORED_FILES = {".DS_Store", "Thumbs.db", ".coverage"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
KNOWN_GENERATED_OUTPUTS = {
    Path(".discovery"),
    Path(".delivery"),
    Path(".delivery-data"),
    Path(".codex/skills"),
    Path(".claude/skills"),
    Path(".agents/skills"),
}


class PackagingError(RuntimeError):
    pass


def _is_ignored_directory(name: str) -> bool:
    return name in IGNORED_DIRECTORIES or name.endswith(".egg-info")


def _is_ignored_file(name: str) -> bool:
    return name in IGNORED_FILES or Path(name).suffix in IGNORED_SUFFIXES


def _is_known_generated_output(relative: Path) -> bool:
    return any(relative == reserved or reserved in relative.parents for reserved in KNOWN_GENERATED_OUTPUTS)


def _validate_omitted_tree(directory: Path, relative: Path, *, staged: bool) -> None:
    """Reject links and special files even inside an excluded generated-output tree."""
    label = "staged" if staged else "source"
    try:
        entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
    except OSError as exc:
        raise PackagingError(f"cannot read {label} directory {directory}: {exc}") from exc

    for entry in entries:
        path = Path(entry.path)
        rel = relative / entry.name
        mode = entry.stat(follow_symlinks=False).st_mode
        if stat.S_ISLNK(mode):
            raise PackagingError(f"{label} symlink is not allowed: {rel}")
        if stat.S_ISDIR(mode):
            _validate_omitted_tree(path, rel, staged=staged)
        elif not stat.S_ISREG(mode):
            if staged:
                raise PackagingError(f"unsupported staged entry: {rel}")
            raise PackagingError(f"unsupported source entry (not a regular file or directory): {rel}")


def _source_path(path: Path) -> Path:
    if path.is_symlink():
        raise PackagingError(f"source root may not be a symlink: {path}")
    try:
        source = path.resolve(strict=True)
    except OSError as exc:
        raise PackagingError(f"source directory does not exist: {path}") from exc
    if not source.is_dir():
        raise PackagingError(f"source is not a directory: {source}")
    return source


def _output_path(path: Path) -> Path:
    expanded = path.expanduser()
    try:
        parent = (expanded.parent if expanded.is_absolute() else Path.cwd() / expanded.parent).resolve(strict=True)
    except OSError as exc:
        raise PackagingError(f"output parent directory does not exist: {expanded.parent}") from exc
    if not parent.is_dir() or not expanded.name:
        raise PackagingError(f"output must name a file in an existing directory: {path}")
    return parent / expanded.name


def _copy_clean_source(source: Path, destination: Path) -> None:
    """Copy regular files only; reject links and special files without following them."""
    destination.mkdir()

    def copy_directory(source_dir: Path, destination_dir: Path, relative: Path) -> None:
        try:
            entries = sorted(os.scandir(source_dir), key=lambda entry: entry.name)
        except OSError as exc:
            raise PackagingError(f"cannot read source directory {source_dir}: {exc}") from exc

        for entry in entries:
            item = Path(entry.path)
            rel = relative / entry.name
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                raise PackagingError(f"source symlink is not allowed: {rel}")
            if stat.S_ISDIR(mode):
                if _is_ignored_directory(entry.name):
                    continue
                if _is_known_generated_output(rel):
                    _validate_omitted_tree(item, rel, staged=False)
                    continue
                child = destination_dir / entry.name
                child.mkdir()
                copy_directory(item, child, rel)
            elif stat.S_ISREG(mode):
                if _is_ignored_file(entry.name):
                    continue
                if _is_known_generated_output(rel):
                    continue
                try:
                    shutil.copy2(item, destination_dir / entry.name, follow_symlinks=False)
                except OSError as exc:
                    raise PackagingError(f"cannot copy {item.relative_to(source)}: {exc}") from exc
            else:
                raise PackagingError(f"unsupported source entry (not a regular file or directory): {item.relative_to(source)}")

    copy_directory(source, destination, Path())


def _iter_clean_files(root: Path):
    """Yield included files in stable order, applying the same rules after verification."""
    def visit(directory: Path, relative: Path):
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise PackagingError(f"cannot read staged directory {directory}: {exc}") from exc

        for entry in entries:
            path = Path(entry.path)
            rel = relative / entry.name
            mode = entry.stat(follow_symlinks=False).st_mode
            if stat.S_ISLNK(mode):
                raise PackagingError(f"staged symlink is not allowed: {rel}")
            if stat.S_ISDIR(mode):
                if _is_ignored_directory(entry.name):
                    continue
                if _is_known_generated_output(rel):
                    _validate_omitted_tree(path, rel, staged=True)
                    continue
                yield from visit(path, rel)
            elif stat.S_ISREG(mode):
                if not _is_ignored_file(entry.name) and not _is_known_generated_output(rel):
                    yield path, rel
            else:
                raise PackagingError(f"unsupported staged entry: {rel}")

    yield from visit(root, Path())


def _run_checked(label: str, command: list[str], cwd: Path, env: dict[str, str]) -> str:
    try:
        result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True)
    except OSError as exc:
        raise PackagingError(f"{label} could not start: {exc}") from exc
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    if result.returncode:
        detail = f"\n{output}" if output else ""
        raise PackagingError(f"{label} failed with exit code {result.returncode}{detail}")
    return output


def _write_archive(root: Path, archive_path: Path) -> None:
    try:
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path, relative in _iter_clean_files(root):
                archive.write(file_path, (Path("discovery") / relative).as_posix())
    except (OSError, zipfile.BadZipFile) as exc:
        raise PackagingError(f"could not create ZIP: {exc}") from exc


def _check_existing_output(output: Path, force: bool) -> None:
    if output.is_symlink():
        raise PackagingError(f"refusing to publish through an output symlink: {output}")
    if output.exists():
        if not output.is_file():
            raise PackagingError(f"output exists and is not a regular file: {output}")
        if not force:
            raise PackagingError(f"output already exists; choose a new path or pass --force for this exact file: {output}")


def _publish(candidate: Path, output: Path, force: bool) -> None:
    _check_existing_output(output, force)
    try:
        if force and output.exists():
            os.replace(candidate, output)
        else:
            # The temporary archive is in the same directory, so this publishes
            # atomically without replacing a file created during the build.
            os.link(candidate, output)
            candidate.unlink()
    except FileExistsError as exc:
        raise PackagingError(f"output appeared during packaging; it was not replaced: {output}") from exc
    except OSError as exc:
        raise PackagingError(f"could not publish archive to {output}: {exc}") from exc


def package(source: Path, output: Path, *, force: bool = False) -> Path:
    source = _source_path(source)
    output = _output_path(output)
    try:
        output.relative_to(source)
    except ValueError:
        pass
    else:
        raise PackagingError(f"output must be outside the source tree: {output}")
    _check_existing_output(output, force)

    with tempfile.TemporaryDirectory(prefix="discovery-package-") as temp_dir:
        work = Path(temp_dir)
        staged = work / "discovery"
        _copy_clean_source(source, staged)

        env = os.environ.copy()
        env["DISCOVERY_SKILL_ROOT"] = str(staged)
        env["PYTHONPATH"] = str(staged / "src")
        env.pop("DISCOVERY_FAST_VALIDATE", None)
        command_dir = work / "bin"
        command_dir.mkdir()
        try:
            (command_dir / "python").symlink_to(sys.executable)
        except OSError as exc:
            raise PackagingError(f"could not bind verification's 'python' command to this interpreter: {exc}") from exc
        env["PATH"] = os.pathsep.join((str(command_dir), env.get("PATH", "")))
        generator = staged / "scripts" / "generate_verification.py"
        if not generator.is_file():
            raise PackagingError("source is missing scripts/generate_verification.py")
        _run_checked("verification generation in clean copy", [sys.executable, str(generator)], staged, env)
        report = staged / "VERIFICATION.md"
        if not report.is_file() or "**Status:** PASS" not in report.read_text(encoding="utf-8"):
            raise PackagingError("verification did not produce a PASS report in the clean copy")

        output.parent.mkdir(parents=False, exist_ok=True)
        fd, candidate_name = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent)
        os.close(fd)
        candidate = Path(candidate_name)
        try:
            _write_archive(staged, candidate)
            if not zipfile.is_zipfile(candidate):
                raise PackagingError("generated candidate is not a valid ZIP")
            try:
                with tempfile.TemporaryDirectory(prefix="discovery-cold-") as cold_dir:
                    with zipfile.ZipFile(candidate) as archive:
                        bad_member = archive.testzip()
                        if bad_member:
                            raise PackagingError(f"ZIP integrity check failed at {bad_member}")
                        archive.extractall(cold_dir)
                    cold = Path(cold_dir) / "discovery"
                    if not cold.is_dir():
                        raise PackagingError("ZIP does not contain the expected discovery/ root")
                    cold_env = env.copy()
                    cold_env["DISCOVERY_SKILL_ROOT"] = str(cold)
                    cold_env["PYTHONPATH"] = str(cold / "src")
                    cold_env["DISCOVERY_FAST_VALIDATE"] = "1"
                    _run_checked(
                        "cold-unpack unit tests",
                        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                        cold,
                        cold_env,
                    )
                    _run_checked(
                        "cold-unpack skill validation",
                        [sys.executable, str(cold / "scripts" / "validate_skill.py")],
                        cold,
                        cold_env,
                    )
            except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
                raise PackagingError(f"cold-unpack validation failed: {exc}") from exc

            _publish(candidate, output, force)
        finally:
            if candidate.exists():
                candidate.unlink()

    return output


def main(argv: list[str] | None = None) -> int:
    default_source = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Create and cold-validate a clean Discovery skill ZIP")
    parser.add_argument("--source", type=Path, default=default_source, help="source skill directory (default: this script's parent)")
    parser.add_argument(
        "--output",
        type=Path,
        default=default_source.parent / DEFAULT_OUTPUT_NAME,
        help=f"new output ZIP path (default: ../{DEFAULT_OUTPUT_NAME})",
    )
    parser.add_argument("--force", action="store_true", help="replace only the exact --output file after all checks pass")
    args = parser.parse_args(argv)
    try:
        result = package(args.source, args.output, force=args.force)
    except PackagingError as exc:
        print(f"package_skill: {exc}", file=sys.stderr)
        return 1
    print(f"Verified clean package: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
