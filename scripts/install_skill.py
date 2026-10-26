#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path


PLATFORMS = {
    "codex": (".codex/skills", "~/.codex/skills"),
    "claude": (".claude/skills", "~/.claude/skills"),
    "agents": (".agents/skills", "~/.agents/skills"),
}
IGNORED_NAMES = {"__pycache__", ".git", ".DS_Store"}


class InstallError(RuntimeError):
    pass


def _ignored(name: str) -> bool:
    return name in IGNORED_NAMES or name.endswith((".pyc", ".zip"))


def ignore(directory, names, excluded_tree: Path | None = None):
    skipped = {name for name in names if _ignored(name)}
    if excluded_tree is not None:
        current = Path(directory)
        skipped.update(name for name in names if current / name == excluded_tree)
    return skipped


def _source_root() -> Path:
    script = Path(__file__).absolute()
    if script.is_symlink() or script.parent.is_symlink():
        raise InstallError("source script or scripts directory may not be a symlink")
    root = script.parents[1]
    if root.is_symlink():
        raise InstallError(f"source root may not be a symlink: {root}")
    try:
        return root.resolve(strict=True)
    except OSError as exc:
        raise InstallError(f"source root is unavailable: {root}") from exc


def _project_root(value: str) -> Path:
    requested = Path(value).expanduser()
    if requested.is_symlink():
        raise InstallError(f"project root may not be a symlink: {requested}")
    try:
        return requested.resolve()
    except OSError as exc:
        raise InstallError(f"cannot resolve project root: {requested}") from exc


def _reject_symlink_components(path: Path, anchor: Path) -> None:
    try:
        relative = path.relative_to(anchor)
    except ValueError as exc:
        raise InstallError(f"installation path is outside its expected root: {path}") from exc
    current = anchor
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise InstallError(f"installation path contains a symlink: {current}")


def _check_tree(root: Path, *, excluded_tree: Path | None = None) -> None:
    """Reject links and special files without following source symlinks."""
    for current, directories, files in os.walk(root, followlinks=False):
        directory = Path(current)
        kept_directories = []
        for name in directories:
            path = directory / name
            if _ignored(name) or path == excluded_tree:
                continue
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                raise InstallError(f"cannot inspect source directory {path}: {exc}") from exc
            if stat.S_ISLNK(mode):
                raise InstallError(f"source symlink is not allowed: {path.relative_to(root)}")
            if not stat.S_ISDIR(mode):
                raise InstallError(f"unsupported source entry: {path.relative_to(root)}")
            kept_directories.append(name)
        directories[:] = kept_directories

        for name in files:
            if _ignored(name):
                continue
            path = directory / name
            try:
                mode = path.lstat().st_mode
            except OSError as exc:
                raise InstallError(f"cannot inspect source file {path}: {exc}") from exc
            if stat.S_ISLNK(mode):
                raise InstallError(f"source symlink is not allowed: {path.relative_to(root)}")
            if not stat.S_ISREG(mode):
                raise InstallError(f"unsupported source entry: {path.relative_to(root)}")


def _place_stage(stage: Path, destination: Path) -> None:
    """Reserve a missing target, then atomically replace the empty reservation."""
    try:
        destination.mkdir()
    except FileExistsError as exc:
        raise InstallError(f"installation target appeared during staging: {destination}") from exc
    try:
        marker = destination.lstat()
    except OSError as exc:
        raise InstallError(f"could not inspect reserved installation target {destination}: {exc}") from exc
    try:
        stage.rename(destination)
    except OSError as exc:
        try:
            current = destination.lstat()
            if (current.st_dev, current.st_ino) == (marker.st_dev, marker.st_ino) and destination.is_dir() and not any(destination.iterdir()):
                destination.rmdir()
        except OSError:
            pass
        raise InstallError(f"could not publish staged installation to {destination}: {exc}") from exc


def _publish(stage: Path, destination: Path, *, force: bool) -> None:
    if destination.is_symlink():
        raise InstallError(f"installation target may not be a symlink: {destination}")
    if not destination.exists():
        _place_stage(stage, destination)
        return
    if not force:
        raise InstallError(f"{destination} exists; use --force to replace this exact install")
    if not destination.is_dir():
        raise InstallError(f"existing installation target is not a directory: {destination}")

    backup_parent = Path(tempfile.mkdtemp(prefix=".discovery-install-backup-", dir=destination.parent))
    backup = backup_parent / "previous"
    try:
        destination.rename(backup)
    except OSError as exc:
        shutil.rmtree(backup_parent, ignore_errors=True)
        raise InstallError(f"could not preserve existing installation before replacement: {exc}") from exc

    try:
        _place_stage(stage, destination)
    except (InstallError, OSError) as publish_error:
        try:
            backup.rename(destination)
        except OSError as rollback_error:
            raise InstallError(
                f"installation failed; previous target remains preserved at {backup}: {rollback_error}"
            ) from publish_error
        shutil.rmtree(backup_parent, ignore_errors=True)
        raise InstallError(f"installation failed; previous target was restored: {publish_error}") from publish_error

    try:
        shutil.rmtree(backup_parent)
    except OSError as exc:
        print(f"Warning: installation succeeded; previous target backup remains at {backup}: {exc}", file=sys.stderr)


def install(platform: str, scope: str, project_root: str, force: bool) -> Path:
    source = _source_root()
    local, global_ = PLATFORMS[platform]
    if scope == "local":
        anchor = _project_root(project_root)
        base = anchor / local
        allowed_internal = source / local / "discovery"
    else:
        anchor = Path.home().resolve()
        base = Path(global_).expanduser()
        allowed_internal = None

    destination = base / "discovery"
    _reject_symlink_components(base, anchor)
    _reject_symlink_components(destination, anchor)

    if destination == source:
        raise InstallError("installation target may not equal the source directory")
    if destination in source.parents:
        raise InstallError("installation target may not be an ancestor of the source directory")
    excluded_tree = None
    if source in destination.parents:
        if destination != allowed_internal:
            raise InstallError("only the default platform skills path may be installed inside the source directory")
        excluded_tree = base

    if destination.is_symlink():
        raise InstallError(f"installation target may not be a symlink: {destination}")
    if destination.exists():
        if not force:
            raise InstallError(f"{destination} exists; use --force to replace this exact install")
        if not destination.is_dir():
            raise InstallError(f"existing installation target is not a directory: {destination}")

    _check_tree(source, excluded_tree=excluded_tree)
    try:
        base.mkdir(parents=True, exist_ok=True)
        _reject_symlink_components(base, anchor)
        with tempfile.TemporaryDirectory(prefix=".discovery-install-stage-", dir=base) as temporary:
            stage = Path(temporary) / "discovery"
            shutil.copytree(
                source,
                stage,
                symlinks=True,
                ignore=lambda directory, names: ignore(directory, names, excluded_tree),
            )
            _check_tree(stage)
            _publish(stage, destination, force=force)
    except InstallError:
        raise
    except (OSError, shutil.Error) as exc:
        raise InstallError(f"installation staging failed; existing target was not replaced: {exc}") from exc
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Discovery into a supported skills directory")
    parser.add_argument("--platform", choices=sorted(PLATFORMS), required=True)
    parser.add_argument("--scope", choices=["local", "global"], default="local")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        destination = install(args.platform, args.scope, args.project_root, args.force)
    except InstallError as exc:
        print(f"install_skill: {exc}", file=sys.stderr)
        return 1
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
