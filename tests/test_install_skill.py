from __future__ import annotations

import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = ROOT / "scripts" / "install_skill.py"
PLATFORM_PATHS = {
    "codex": ".codex/skills",
    "claude": ".claude/skills",
    "agents": ".agents/skills",
}


def _put(root: Path, relative: str, content: str | bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


def _source(parent: Path, *, path: Path | None = None) -> Path:
    source = path if path is not None else parent / "source"
    source.mkdir(parents=True, exist_ok=True)
    (source / "scripts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(INSTALL_SCRIPT, source / "scripts" / "install_skill.py")
    _put(source, "SKILL.md", "fixture skill\n")
    _put(source, "sentinel.txt", "source payload\n")
    _put(source, ".well-known/reference.md", "required hidden reference\n")
    _put(source, ".github/workflows/ci.yml", "name: hidden workflow\n")
    _put(source, ".custom-hidden/asset.bin", b"hidden asset")
    _put(source, ".git/config", "repository metadata\n")
    _put(source, "__pycache__/cached.pyc", b"bytecode")
    _put(source, "scripts/ignored.pyc", b"bytecode")
    _put(source, ".DS_Store", "finder metadata\n")
    _put(source, "old-install.zip", b"generated archive")
    executable = _put(source, "scripts/executable.sh", "#!/bin/sh\nexit 0\n")
    executable.chmod(0o751)
    return source


def _destination(root: Path, platform: str) -> Path:
    return root.resolve() / PLATFORM_PATHS[platform] / "discovery"


def _run_install(
    source: Path,
    platform: str,
    *extra: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(source / "scripts" / "install_skill.py"), "--platform", platform, *extra],
        cwd=cwd or source,
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
    )


def _load_installer(source: Path):
    script = source / "scripts" / "install_skill.py"
    spec = importlib.util.spec_from_file_location("fixture_install_skill", script)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load fixture installer: {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-install-skill-")
        self.parent = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_install_inside_source_works_for_all_platforms(self):
        for platform in PLATFORM_PATHS:
            with self.subTest(platform=platform):
                source = _source(self.parent / platform)
                result = _run_install(source, platform)
                destination = _destination(source, platform)

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(Path(result.stdout.strip()), destination)
                self.assertTrue((destination / "SKILL.md").is_file())
                self.assertEqual((destination / "sentinel.txt").read_text(encoding="utf-8"), "source payload\n")
                self.assertTrue((destination / ".well-known/reference.md").is_file())
                self.assertTrue((destination / ".github/workflows/ci.yml").is_file())
                self.assertTrue((destination / ".custom-hidden/asset.bin").is_file())
                self.assertFalse((destination / ".git").exists())
                self.assertFalse((destination / "__pycache__").exists())
                self.assertFalse((destination / ".DS_Store").exists())
                self.assertFalse((destination / "scripts/ignored.pyc").exists())
                self.assertFalse((destination / "old-install.zip").exists())
                self.assertFalse((destination / PLATFORM_PATHS[platform] / "discovery").exists())
                mode = stat.S_IMODE((destination / "scripts/executable.sh").stat().st_mode)
                self.assertEqual(mode, 0o751)

    def test_external_local_project_root_works_for_all_platforms(self):
        for platform in PLATFORM_PATHS:
            with self.subTest(platform=platform):
                case = self.parent / f"external-{platform}"
                source = _source(case / "source")
                project = case / "project"
                project.mkdir(parents=True)
                result = _run_install(source, platform, "--scope", "local", "--project-root", str(project))

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                destination = _destination(project, platform)
                self.assertTrue((destination / "sentinel.txt").is_file())
                self.assertFalse((source / PLATFORM_PATHS[platform] / "discovery").exists())

    def test_global_scope_uses_only_an_isolated_home_for_all_platforms(self):
        for platform in PLATFORM_PATHS:
            with self.subTest(platform=platform):
                case = self.parent / f"global-{platform}"
                source = _source(case / "source")
                isolated_home = case / "home"
                isolated_home.mkdir(parents=True)
                env = os.environ.copy()
                env["HOME"] = str(isolated_home.resolve())

                result = _run_install(source, platform, "--scope", "global", env=env)

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                destination = _destination(isolated_home, platform)
                self.assertEqual(Path(result.stdout.strip()), destination)
                self.assertTrue((destination / "sentinel.txt").is_file())

    def test_existing_target_is_refused_without_force_and_left_unchanged(self):
        source = _source(self.parent)
        project = self.parent / "project"
        destination = _destination(project, "codex")
        _put(destination, "keep.txt", "old install stays\n")
        before = sorted((path.relative_to(destination).as_posix(), path.read_bytes()) for path in destination.rglob("*") if path.is_file())

        result = _run_install(source, "codex", "--project-root", str(project))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exists; use --force", result.stderr)
        after = sorted((path.relative_to(destination).as_posix(), path.read_bytes()) for path in destination.rglob("*") if path.is_file())
        self.assertEqual(after, before)

    def test_force_replaces_only_the_exact_install_and_keeps_sibling_skills(self):
        source = _source(self.parent)
        project = self.parent / "project"
        destination = _destination(project, "codex")
        _put(destination, "old-only.txt", "remove this old target file\n")
        sibling = destination.parent / "another-skill"
        _put(sibling, "keep.txt", "leave sibling install alone\n")

        result = _run_install(source, "codex", "--project-root", str(project), "--force")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((destination / "sentinel.txt").is_file())
        self.assertFalse((destination / "old-only.txt").exists())
        self.assertEqual((sibling / "keep.txt").read_text(encoding="utf-8"), "leave sibling install alone\n")

    def test_force_publish_failure_restores_the_previous_target(self):
        source = _source(self.parent)
        project = self.parent / "project"
        destination = _destination(project, "codex")
        _put(destination, "keep.txt", "old installation must survive\n")
        installer = _load_installer(source)
        original_rename = Path.rename

        def fail_stage_rename(path: Path, target: Path) -> Path:
            if path.name == "discovery" and path.parent.name.startswith(".discovery-install-stage-"):
                raise OSError("injected stage publish failure")
            return original_rename(path, target)

        with patch.object(Path, "rename", fail_stage_rename):
            with self.assertRaisesRegex(installer.InstallError, "previous target was restored"):
                installer.install("codex", "local", str(project), True)

        self.assertEqual((destination / "keep.txt").read_text(encoding="utf-8"), "old installation must survive\n")
        self.assertFalse((destination / "sentinel.txt").exists())
        self.assertEqual(list(destination.parent.glob(".discovery-install-backup-*")), [])

    def test_failed_source_symlink_check_preserves_existing_install(self):
        source = _source(self.parent)
        outside = self.parent / "outside-secret.txt"
        outside.write_text("never copy this external file\n", encoding="utf-8")
        link = source / "references/external.txt"
        link.parent.mkdir()
        try:
            link.symlink_to(outside)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        project = self.parent / "project"
        destination = _destination(project, "codex")
        _put(destination, "keep.txt", "old install stays\n")
        result = _run_install(source, "codex", "--project-root", str(project), "--force")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source symlink is not allowed", result.stderr)
        self.assertEqual((destination / "keep.txt").read_text(encoding="utf-8"), "old install stays\n")
        self.assertFalse((destination / "references/external.txt").exists())
        self.assertEqual(outside.read_text(encoding="utf-8"), "never copy this external file\n")

    def test_project_root_source_and_target_symlinks_are_refused(self):
        source = _source(self.parent / "source-case")
        real_project = self.parent / "real-project"
        real_project.mkdir()
        project_link = self.parent / "project-link"
        try:
            project_link.symlink_to(real_project, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        linked_root = _run_install(source, "codex", "--project-root", str(project_link))
        self.assertNotEqual(linked_root.returncode, 0)
        self.assertIn("project root may not be a symlink", linked_root.stderr)
        self.assertFalse((real_project / ".codex").exists())

        source_link = self.parent / "source-link"
        source_link.symlink_to(source, target_is_directory=True)
        linked_source = _run_install(source_link, "codex", cwd=source_link)
        self.assertNotEqual(linked_source.returncode, 0)
        self.assertIn("source root may not be a symlink", linked_source.stderr)
        self.assertFalse((source / ".codex").exists())

        outside = self.parent / "outside-install"
        _put(outside, "keep.txt", "outside target remains\n")
        target_project = self.parent / "target-project"
        skills = target_project / ".codex/skills"
        skills.mkdir(parents=True)
        target = skills / "discovery"
        target.symlink_to(outside, target_is_directory=True)
        target_link = _run_install(source, "codex", "--project-root", str(target_project), "--force")
        self.assertNotEqual(target_link.returncode, 0)
        self.assertIn("symlink", target_link.stderr)
        self.assertTrue(target.is_symlink())
        self.assertEqual((outside / "keep.txt").read_text(encoding="utf-8"), "outside target remains\n")

    def test_symlinked_target_ancestor_and_existing_file_are_refused_before_force(self):
        source = _source(self.parent / "source")
        outside = self.parent / "outside-base"
        outside.mkdir()
        project = self.parent / "symlinked-base-project"
        (project / ".codex").mkdir(parents=True)
        try:
            (project / ".codex/skills").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")

        ancestor = _run_install(source, "codex", "--project-root", str(project), "--force")
        self.assertNotEqual(ancestor.returncode, 0)
        self.assertIn("installation path contains a symlink", ancestor.stderr)
        self.assertEqual(list(outside.iterdir()), [])

        project = self.parent / "file-target-project"
        destination = _destination(project, "codex")
        destination.parent.mkdir(parents=True)
        destination.write_text("do not remove user file\n", encoding="utf-8")
        file_target = _run_install(source, "codex", "--project-root", str(project), "--force")
        self.assertNotEqual(file_target.returncode, 0)
        self.assertIn("not a directory", file_target.stderr)
        self.assertEqual(destination.read_text(encoding="utf-8"), "do not remove user file\n")

    def test_source_target_ancestor_and_unapproved_nested_paths_are_refused(self):
        project = self.parent / "same-source-project"
        source = _source(project, path=_destination(project, "codex"))
        _put(source, "do-not-delete.txt", "source must survive\n")
        same_target = _run_install(source, "codex", "--project-root", str(project), "--force")
        self.assertNotEqual(same_target.returncode, 0)
        self.assertIn("target may not equal the source", same_target.stderr)
        self.assertTrue((source / "do-not-delete.txt").is_file())

        project = self.parent / "ancestor-project"
        source_path = _destination(project, "codex") / "nested-source"
        source = _source(project, path=source_path)
        _put(source, "do-not-delete.txt", "nested source must survive\n")
        ancestor_target = _run_install(source, "codex", "--project-root", str(project), "--force")
        self.assertNotEqual(ancestor_target.returncode, 0)
        self.assertIn("ancestor of the source", ancestor_target.stderr)
        self.assertTrue((source / "do-not-delete.txt").is_file())

        source = _source(self.parent / "nested-target-source")
        nested_project = source / "subproject"
        nested_project.mkdir()
        nested_target = _run_install(source, "codex", "--project-root", str(nested_project))
        self.assertNotEqual(nested_target.returncode, 0)
        self.assertIn("only the default platform skills path", nested_target.stderr)
        self.assertFalse((nested_project / ".codex").exists())


if __name__ == "__main__":
    unittest.main()
