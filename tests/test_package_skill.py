from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SCRIPT = ROOT / "scripts" / "package_skill.py"
INSTALL_SCRIPT = ROOT / "scripts" / "install_skill.py"


def _put(root: Path, relative: str, content: str | bytes) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")
    return path


ISOLATION_PROBE = "package_isolation_probe_7c4b"


def _fixture_source(
    parent: Path,
    *,
    fail_generation: bool = False,
    stage_probe: bool = False,
    cold_probe: bool = False,
    path_probe: bool = False,
    post_verify_outputs: bool = False,
) -> Path:
    parent.mkdir(parents=True, exist_ok=True)
    source = parent / "source-tree"
    source.mkdir()
    (source / "scripts").mkdir()
    (source / "tests").mkdir()
    shutil.copy2(PACKAGE_SCRIPT, source / "scripts" / "package_skill.py")
    (source / "scripts" / "package_skill.py").chmod(0o755)
    shutil.copy2(INSTALL_SCRIPT, source / "scripts" / "install_skill.py")

    generator = """from pathlib import Path
import os
import sys
root = Path(__file__).resolve().parents[1]
if root.name != 'discovery':
    raise SystemExit('staged root must be named discovery')
if os.environ.get('DISCOVERY_FAST_VALIDATE'):
    raise SystemExit('stage verification must not inherit fast validation')
if FAILURE:
    raise SystemExit(7)
(root / 'VERIFICATION.md').write_text('# Verification Report\\n\\n- **Status:** PASS\\n', encoding='utf-8')
if POST_VERIFY_OUTPUTS:
    for relative in (
        '.discovery/post-verification-marker.txt',
        '.delivery/post-verification-marker.txt',
        '.delivery-data/post-verification-marker.txt',
        '.codex/skills/post-verification-marker.txt',
        '.claude/skills/post-verification-marker.txt',
        '.agents/skills/post-verification-marker.txt',
    ):
        marker = root / relative
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text('generated during verification\\n', encoding='utf-8')
""".replace("FAILURE", repr(fail_generation)).replace("POST_VERIFY_OUTPUTS", repr(post_verify_outputs))
    if stage_probe:
        generator = f"import {ISOLATION_PROBE}\n" + generator
    if path_probe:
        path_check = """import subprocess
child = subprocess.run(['python', '-c', "from pathlib import Path; Path('python-child-ran').write_text('ok')"], cwd=root)
if child.returncode or not (root / 'python-child-ran').is_file():
    raise SystemExit('stage did not use the bound python command')
"""
        generator = generator.replace("if root.name", path_check + "if root.name")
    _put(source, "scripts/generate_verification.py", generator)
    _put(
        source,
        "scripts/validate_skill.py",
        """from pathlib import Path
root = Path(__file__).resolve().parents[1]
assert root.name == 'discovery'
assert (root / '.well-known' / 'asset.md').is_file()
assert (root / '.github' / 'workflows' / 'ci.yml').is_file()
assert (root / 'VERIFICATION.md').is_file()
assert not (root / 'node_modules').exists()
assert not (root / '.venv').exists()
assert not (root / 'build').exists()
assert not (root / 'dist').exists()
print('fixture skill validated')
""",
    )
    _put(
        source,
        "tests/test_fixture.py",
        """from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class PackagedFixtureTests(unittest.TestCase):
    def test_clean_copy_and_hidden_assets(self):
        self.assertEqual(ROOT.name, 'discovery')
        self.assertTrue((ROOT / '.well-known' / 'asset.md').is_file())
        self.assertTrue((ROOT / '.github' / 'workflows' / 'ci.yml').is_file())
        self.assertTrue((ROOT / 'VERIFICATION.md').is_file())
        for relative in ('.git', '__pycache__', '.pytest_cache', '.venv', 'node_modules', 'build', 'dist', 'src/example.egg-info'):
            self.assertFalse((ROOT / relative).exists(), relative)
        self.assertFalse((ROOT / 'src' / 'example.pyc').exists())
""",
    )
    if cold_probe:
        test_path = source / "tests" / "test_fixture.py"
        test_path.write_text(f"import {ISOLATION_PROBE}\n" + test_path.read_text(encoding="utf-8"), encoding="utf-8")

    _put(source, ".gitignore", "local-build/\n")
    _put(source, ".well-known/asset.md", "required hidden reference\n")
    _put(source, ".github/workflows/ci.yml", "name: hidden workflow asset\n")
    _put(source, "src/example.py", "VALUE = 1\n")
    _put(source, "src/example.pyc", b"compiled-cache")
    _put(source, ".git/config", "repository metadata\n")
    _put(source, "__pycache__/module.pyc", b"cached-bytecode")
    _put(source, ".pytest_cache/v/cache/nodeids", "[]\n")
    _put(source, ".venv/lib/site.py", "dependency\n")
    _put(source, "node_modules/example/index.js", "dependency\n")
    _put(source, "build/output.bin", b"build output")
    _put(source, "dist/output.whl", b"build output")
    _put(source, "src/example.egg-info/PKG-INFO", "generated metadata\n")
    _put(source, ".DS_Store", "finder metadata\n")
    executable = source / "scripts" / "validate_skill.py"
    executable.chmod(0o751)
    return source


def _snapshot(root: Path) -> dict[str, tuple[str, bytes | int | str]]:
    result: dict[str, tuple[str, bytes | int | str]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISLNK(mode):
            result[relative] = ("symlink", os.readlink(path))
        elif stat.S_ISDIR(mode):
            result[relative] = ("dir", stat.S_IMODE(mode))
        else:
            result[relative] = ("file", path.read_bytes())
    return result


class PackageSkillTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="test-package-skill-")
        self.parent = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def run_package(
        self,
        source: Path,
        output: Path,
        *extra: str,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(source / "scripts" / "package_skill.py"), "--source", str(source), "--output", str(output), *extra],
            env=env,
            text=True,
            capture_output=True,
            timeout=90,
        )

    def test_source_internal_installs_and_verification_outputs_are_excluded(self):
        source = _fixture_source(self.parent, post_verify_outputs=True)
        authored_and_similar_paths = {
            ".codex/settings-ref/interop-probe-marker.txt": "authored Codex reference\n",
            ".well-known/interop-probe-marker.txt": "authored hidden reference\n",
            ".discovery-copy/keep.md": "similar prefix\n",
            ".delivery-copy/keep.md": "similar prefix\n",
            ".delivery-data-copy/keep.md": "similar prefix\n",
            ".codex/skills-reference/keep.md": "similar prefix\n",
            "references/.discovery/keep.md": "nested reference\n",
            "references/.delivery/keep.md": "nested reference\n",
            "references/.delivery-data/keep.md": "nested reference\n",
            "references/.codex/skills/keep.md": "nested reference\n",
        }
        for relative, content in authored_and_similar_paths.items():
            _put(source, relative, content)
        for relative in (
            ".discovery/source-marker.txt",
            ".delivery/source-marker.txt",
            ".delivery-data/source-marker.txt",
        ):
            _put(source, relative, "source-side generated state\n")

        # Exercise the installer's default local scope and implicit project root
        # against the source itself for every supported client.
        for platform in ("codex", "claude", "agents"):
            installed = subprocess.run(
                [sys.executable, str(source / "scripts" / "install_skill.py"), "--platform", platform],
                cwd=source,
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(installed.returncode, 0, installed.stdout + installed.stderr)
            self.assertTrue((source / f".{platform}" / "skills" / "discovery" / "scripts" / "package_skill.py").is_file())

        source_before = _snapshot(source)
        output = self.parent / "source-internal-install.zip"
        result = self.run_package(source, output)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(_snapshot(source), source_before)
        with zipfile.ZipFile(output) as archive:
            self.assertIsNone(archive.testzip())
            names = set(archive.namelist())
            for relative in (
                ".discovery",
                ".delivery",
                ".delivery-data",
                ".codex/skills",
                ".claude/skills",
                ".agents/skills",
            ):
                prefix = f"discovery/{relative}"
                self.assertFalse(
                    any(name == prefix or name.startswith(prefix + "/") for name in names),
                    f"reserved generated output was packaged: {prefix}",
                )
            for relative in (
                ".codex/settings-ref/interop-probe-marker.txt",
                ".well-known/interop-probe-marker.txt",
                ".discovery-copy/keep.md",
                ".delivery-copy/keep.md",
                ".delivery-data-copy/keep.md",
                ".codex/skills-reference/keep.md",
                "references/.discovery/keep.md",
                "references/.delivery/keep.md",
                "references/.delivery-data/keep.md",
                "references/.codex/skills/keep.md",
            ):
                self.assertIn(f"discovery/{relative}", names)

    def test_symlinks_inside_known_generated_outputs_are_still_rejected(self):
        source = _fixture_source(self.parent)
        external = self.parent / "outside-generated-tree.txt"
        external.write_text("must not be followed", encoding="utf-8")
        link = source / ".delivery" / "linked.txt"
        link.parent.mkdir()
        try:
            link.symlink_to(external)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        output = self.parent / "reserved-symlink.zip"

        result = self.run_package(source, output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source symlink is not allowed", result.stderr)
        self.assertFalse(output.exists())
        self.assertEqual(external.read_text(encoding="utf-8"), "must not be followed")

    def test_special_files_inside_known_generated_outputs_are_still_rejected(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("named pipes unavailable")
        source = _fixture_source(self.parent)
        generated = source / ".delivery" / "unsupported.pipe"
        generated.parent.mkdir()
        os.mkfifo(generated)
        output = self.parent / "reserved-special-file.zip"

        result = self.run_package(source, output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported source entry", result.stderr)
        self.assertFalse(output.exists())

    def test_clean_zip_preserves_hidden_assets_permissions_and_cold_unpacks(self):
        source = _fixture_source(self.parent)
        output = self.parent / "candidate.zip"
        old_archive = self.parent / "discovery-v0.3.zip"
        old_archive.write_bytes(b"pre-existing archive: do not touch")
        source_before = _snapshot(source)
        old_archive_before = old_archive.read_bytes()

        result = self.run_package(source, output)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Verified clean package", result.stdout)
        self.assertEqual(_snapshot(source), source_before)
        self.assertEqual(old_archive.read_bytes(), old_archive_before)
        self.assertTrue(zipfile.is_zipfile(output))
        with zipfile.ZipFile(output) as archive:
            self.assertIsNone(archive.testzip())
            names = archive.namelist()
            self.assertTrue(names)
            self.assertTrue(all(name.startswith("discovery/") for name in names))
            self.assertIn("discovery/VERIFICATION.md", names)
            self.assertIn("discovery/.well-known/asset.md", names)
            self.assertIn("discovery/.github/workflows/ci.yml", names)
            self.assertIn("discovery/.gitignore", names)
            self.assertIn("discovery/scripts/package_skill.py", names)
            self.assertFalse(any(".git/" in name or "__pycache__/" in name for name in names))
            self.assertFalse(any(".pytest_cache/" in name or ".venv/" in name for name in names))
            self.assertFalse(any("node_modules/" in name or "/build/" in name or "/dist/" in name for name in names))
            self.assertFalse(any(name.endswith((".pyc", ".pyo", ".DS_Store")) or ".egg-info/" in name for name in names))
            validate_info = archive.getinfo("discovery/scripts/validate_skill.py")
            self.assertEqual(stat.S_IMODE(validate_info.external_attr >> 16), 0o751)
            package_info = archive.getinfo("discovery/scripts/package_skill.py")
            self.assertEqual(stat.S_IMODE(package_info.external_attr >> 16), 0o755)

            cold_parent = self.parent / "manual-cold-unpack"
            cold_parent.mkdir()
            archive.extractall(cold_parent)

        cold = self.parent / "manual-cold-unpack" / "discovery"
        cold_env = os.environ.copy()
        cold_env["DISCOVERY_SKILL_ROOT"] = str(cold)
        cold_env["PYTHONPATH"] = os.pathsep.join(
            item for item in (str(cold / "src"), cold_env.get("PYTHONPATH", "")) if item
        )
        cold_tests = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=cold,
            env=cold_env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(cold_tests.returncode, 0, cold_tests.stdout + cold_tests.stderr)
        cold_validation = subprocess.run(
            [sys.executable, str(cold / "scripts" / "validate_skill.py")],
            cwd=cold,
            env=cold_env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(cold_validation.returncode, 0, cold_validation.stdout + cold_validation.stderr)

    def test_existing_output_is_not_overwritten_without_force(self):
        source = _fixture_source(self.parent)
        output = self.parent / "existing.zip"
        output.write_bytes(b"keep this exact old archive")
        before = output.read_bytes()

        result = self.run_package(source, output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output already exists", result.stderr)
        self.assertEqual(output.read_bytes(), before)

    def test_failed_verification_does_not_replace_forced_output_or_other_archives(self):
        source = _fixture_source(self.parent, fail_generation=True)
        output = self.parent / "explicit-target.zip"
        other_archive = self.parent / "old-release.zip"
        output.write_bytes(b"target remains until successful validation")
        other_archive.write_bytes(b"another release remains untouched")
        target_before = output.read_bytes()
        other_before = other_archive.read_bytes()

        result = self.run_package(source, output, "--force")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("verification generation in clean copy failed", result.stderr)
        self.assertEqual(output.read_bytes(), target_before)
        self.assertEqual(other_archive.read_bytes(), other_before)

    def test_successful_force_replaces_only_the_exact_output(self):
        source = _fixture_source(self.parent)
        output = self.parent / "explicit-target.zip"
        other_archive = self.parent / "old-release.zip"
        output.write_bytes(b"replace only with explicit force")
        other_archive.write_bytes(b"preserve this archive")
        other_before = other_archive.read_bytes()

        result = self.run_package(source, output, "--force")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(zipfile.is_zipfile(output))
        self.assertEqual(other_archive.read_bytes(), other_before)

    def test_source_symlink_is_rejected_without_publishing_external_content(self):
        source = _fixture_source(self.parent)
        secret = self.parent / "outside-secret.txt"
        secret.write_text("must never be followed into the package", encoding="utf-8")
        link = source / "references" / "external.txt"
        link.parent.mkdir()
        try:
            link.symlink_to(secret)
        except OSError as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        output = self.parent / "must-not-exist.zip"

        result = self.run_package(source, output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source symlink is not allowed", result.stderr)
        self.assertFalse(output.exists())
        self.assertEqual(secret.read_text(encoding="utf-8"), "must never be followed into the package")

    def test_output_inside_source_tree_is_rejected(self):
        source = _fixture_source(self.parent)
        output = source / "candidate.zip"

        result = self.run_package(source, output)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("output must be outside the source tree", result.stderr)
        self.assertFalse(output.exists())

    def test_stage_verification_clears_caller_fast_validate_shortcut(self):
        source = _fixture_source(self.parent)
        output = self.parent / "full-stage-validation.zip"
        env = os.environ.copy()
        env["DISCOVERY_FAST_VALIDATE"] = "1"

        result = self.run_package(source, output, env=env)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(zipfile.is_zipfile(output))

    def test_stage_verification_ignores_caller_python_path_shim(self):
        decoy_dir = self.parent / "python-path-decoy"
        decoy_dir.mkdir()
        decoy = _put(decoy_dir, "python", "#!/bin/sh\nexit 0\n")
        decoy.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = os.pathsep.join((str(decoy_dir), env.get("PATH", "")))
        source = _fixture_source(self.parent / "path-probe", path_probe=True)
        output = self.parent / "path-bound-validation.zip"

        result = self.run_package(source, output, env=env)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        with zipfile.ZipFile(output) as archive:
            self.assertIn("discovery/python-child-ran", archive.namelist())

    def test_verification_and_cold_tests_do_not_borrow_caller_pythonpath(self):
        decoy_dir = self.parent / "caller-pythonpath"
        decoy_dir.mkdir()
        _put(decoy_dir, f"{ISOLATION_PROBE}.py", "VALUE = 'external decoy'\n")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(decoy_dir)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        stage_source = _fixture_source(self.parent / "stage-probe", stage_probe=True)
        stage_output = self.parent / "stage-probe.zip"
        stage_result = self.run_package(stage_source, stage_output, env=env)
        self.assertNotEqual(stage_result.returncode, 0)
        self.assertIn("verification generation in clean copy failed", stage_result.stderr)
        self.assertFalse(stage_output.exists())

        cold_source = _fixture_source(self.parent / "cold-probe", cold_probe=True)
        cold_output = self.parent / "cold-probe.zip"
        cold_output.write_bytes(b"preserve on cold validation failure")
        before = cold_output.read_bytes()
        cold_result = self.run_package(cold_source, cold_output, "--force", env=env)
        self.assertNotEqual(cold_result.returncode, 0)
        self.assertIn("cold-unpack unit tests failed", cold_result.stderr)
        self.assertEqual(cold_output.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
