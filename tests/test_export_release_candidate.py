"""Tests for deterministic, privacy-bounded public candidate export."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from unittest import mock


SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SOURCE_ROOT.parent
EXPORTER = SOURCE_ROOT / "scripts" / "export_release_candidate.py"
VALIDATOR = SOURCE_ROOT / "tests" / "validate_suite.py"
PLUGIN_NAME = "research-skills-suite"


def load_exporter_module():
    module_name = "release_candidate_exporter_under_test"
    specification = importlib.util.spec_from_file_location(module_name, EXPORTER)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load export_release_candidate.py")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


EXPORTER_MODULE = load_exporter_module()


@contextmanager
def temporary_area() -> Iterator[Path]:
    root = WORKSPACE_ROOT / f".skill-export-test-{uuid.uuid4().hex}"
    root.mkdir(parents=False, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root)


def export_command(
    target: Path,
    *extra: str,
    source: Path = SOURCE_ROOT,
) -> list[str]:
    return [
        sys.executable,
        str(EXPORTER),
        "--source",
        str(source),
        "--output",
        str(target),
        "--author-name",
        "Suite Maintainer",
        "--author-url",
        "https://github.com/research-suite-owner",
        "--repository-url",
        "https://github.com/research-suite-owner/research-skills-suite",
        "--homepage-url",
        "https://github.com/research-suite-owner/research-skills-suite",
        "--support-url",
        "https://github.com/research-suite-owner/research-skills-suite/issues",
        "--privacy-policy-url",
        "https://github.com/research-suite-owner/research-skills-suite/blob/main/PRIVACY.md",
        "--terms-of-service-url",
        "https://github.com/research-suite-owner/research-skills-suite/blob/main/TERMS.md",
        "--license",
        "Apache-2.0",
        "--description",
        "Traceable and reproducible research workflows for Codex.",
        *extra,
    ]


def run_export(
    target: Path,
    *extra: str,
    source: Path = SOURCE_ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        export_command(target, *extra, source=source),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )


def exporter_args(source: Path, target: Path) -> argparse.Namespace:
    return argparse.Namespace(
        source=source,
        output=target,
        plugin_name=PLUGIN_NAME,
        author_name="Suite Maintainer",
        author_url="https://github.com/research-suite-owner",
        repository_url="https://github.com/research-suite-owner/research-skills-suite",
        homepage_url="https://github.com/research-suite-owner/research-skills-suite",
        support_url="https://github.com/research-suite-owner/research-skills-suite/issues",
        privacy_policy_url=(
            "https://github.com/research-suite-owner/research-skills-suite/"
            "blob/main/PRIVACY.md"
        ),
        terms_of_service_url=(
            "https://github.com/research-suite-owner/research-skills-suite/"
            "blob/main/TERMS.md"
        ),
        license="Apache-2.0",
        description="Traceable and reproducible research workflows for Codex.",
        display_name="Research Skills Suite",
        category="Productivity",
        keyword=[],
        expected_version=None,
    )


def copy_source(destination: Path) -> Path:
    return Path(
        shutil.copytree(
            SOURCE_ROOT,
            destination,
            ignore=shutil.ignore_patterns(
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
            ),
        )
    )


def file_snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ExportReleaseCandidateTests(unittest.TestCase):
    def test_real_source_exports_public_layout_and_static_passes(self) -> None:
        with temporary_area() as area:
            target = area / PLUGIN_NAME
            completed = run_export(target)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr or completed.stdout,
            )
            self.assertTrue((target / ".codex-plugin" / "plugin.json").is_file())
            self.assertTrue((target / "tests" / "run_release_checks.py").is_file())
            self.assertTrue(
                (target / "scripts" / "export_release_candidate.py").is_file()
            )
            skills = {
                path.parent.name
                for path in (target / "skills").glob("*/SKILL.md")
            }
            self.assertEqual(len(skills), 8)
            self.assertFalse((target / "PLUGIN_RELEASE.md").exists())
            self.assertFalse((target / ".git").exists())
            for name in (
                "CONTRIBUTING.md",
                "PRIVACY.md",
                "SECURITY.md",
                "SUPPORT.md",
                "TERMS.md",
            ):
                if (SOURCE_ROOT / name).is_file():
                    self.assertEqual(
                        (target / name).read_bytes(),
                        (SOURCE_ROOT / name).read_bytes(),
                    )
            readme = (target / "README.md").read_text(encoding="utf-8")
            self.assertNotIn("PLUGIN_RELEASE", readme)

            manifest = json.loads(
                (target / ".codex-plugin" / "plugin.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["name"], PLUGIN_NAME)
            self.assertEqual(manifest["author"]["name"], "Suite Maintainer")
            self.assertEqual(manifest["skills"], "./skills/")
            self.assertEqual(
                manifest["interface"]["privacyPolicyURL"],
                "https://github.com/research-suite-owner/research-skills-suite/"
                "blob/main/PRIVACY.md",
            )
            self.assertEqual(
                manifest["interface"]["termsOfServiceURL"],
                "https://github.com/research-suite-owner/research-skills-suite/"
                "blob/main/TERMS.md",
            )
            release = json.loads(
                (target / "RELEASE_MANIFEST.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                release["inventory"]["file_count"],
                len(file_snapshot(target)) - 1,
            )
            self.assertIn(
                "package-local consistency only",
                release["inventory"]["assurance"],
            )

            validation = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--root",
                    str(target),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
            )
            self.assertEqual(
                validation.returncode,
                0,
                validation.stderr or validation.stdout,
            )
            self.assertIn("layout=public-plugin", validation.stdout)

    def test_export_is_byte_deterministic(self) -> None:
        with temporary_area() as area:
            first = area / "first" / PLUGIN_NAME
            second = area / "second" / PLUGIN_NAME
            first.parent.mkdir()
            second.parent.mkdir()
            first_result = run_export(first)
            second_result = run_export(second)
            self.assertEqual(first_result.returncode, 0, first_result.stderr)
            self.assertEqual(second_result.returncode, 0, second_result.stderr)
            self.assertEqual(file_snapshot(first), file_snapshot(second))

    def test_checksum_inventory_is_exact_and_detects_tampering(self) -> None:
        with temporary_area() as area:
            target = area / PLUGIN_NAME
            completed = run_export(target)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            checksum_lines = (
                target / "SHA256SUMS"
            ).read_text(encoding="utf-8").splitlines()
            declared: dict[str, str] = {}
            for line in checksum_lines:
                digest, relative = line.split("  ", 1)
                declared[relative] = digest
            actual_files = {
                path.relative_to(target).as_posix(): path
                for path in target.rglob("*")
                if path.is_file() and path.name != "SHA256SUMS"
            }
            self.assertEqual(set(declared), set(actual_files))
            for relative, path in actual_files.items():
                self.assertEqual(
                    declared[relative],
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )

            with (target / "README.md").open(
                "a", encoding="utf-8", newline="\n"
            ) as handle:
                handle.write("\ntampered\n")
            validation = subprocess.run(
                [
                    sys.executable,
                    str(VALIDATOR),
                    "--root",
                    str(target),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
            )
            self.assertEqual(validation.returncode, 1)
            self.assertIn("digest mismatch", validation.stdout)

    def test_nonempty_target_is_rejected_without_overwrite(self) -> None:
        with temporary_area() as area:
            target = area / PLUGIN_NAME
            target.mkdir()
            sentinel = target / "keep.txt"
            sentinel.write_text("keep\n", encoding="utf-8")
            completed = run_export(target)
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
            self.assertIn("not empty", completed.stderr)

    def test_empty_target_is_also_rejected_without_replacement(self) -> None:
        with temporary_area() as area:
            target = area / PLUGIN_NAME
            target.mkdir()
            before = os.lstat(target).st_ino
            completed = run_export(target)
            self.assertEqual(completed.returncode, 2)
            self.assertTrue(target.is_dir())
            self.assertEqual(os.lstat(target).st_ino, before)
            self.assertIn("never overwritten", completed.stderr)

    def test_placeholder_metadata_is_rejected_without_traceback(self) -> None:
        with temporary_area() as area:
            target = area / PLUGIN_NAME
            command = export_command(target)
            author_index = command.index("--author-name") + 1
            command[author_index] = "Local developer"
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
            )
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())
            self.assertIn("placeholder metadata", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_privacy_and_terms_urls_are_mandatory_https_metadata(self) -> None:
        with temporary_area() as area:
            target = area / PLUGIN_NAME
            command = export_command(target)
            privacy_index = command.index("--privacy-policy-url") + 1
            command[privacy_index] = "http://example.invalid/PRIVACY.md"
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
            )
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())
            self.assertIn("privacy policy URL must be an absolute https URL", completed.stderr)

            del command[privacy_index]
            del command[privacy_index - 1]
            missing = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
            )
            self.assertEqual(missing.returncode, 2)
            self.assertFalse(target.exists())
            self.assertIn("--privacy-policy-url", missing.stderr)

    def test_output_directory_must_match_plugin_name(self) -> None:
        with temporary_area() as area:
            target = area / "wrong-name"
            completed = run_export(target)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())
            self.assertIn("must exactly match", completed.stderr)

    def test_source_root_symlink_is_rejected_without_following(self) -> None:
        with temporary_area() as area:
            alias = area / "source-link"
            try:
                os.symlink(SOURCE_ROOT, alias, target_is_directory=True)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"directory symlink unavailable on this Windows host: {exc}")
            target = area / PLUGIN_NAME
            completed = run_export(target, source=alias)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())
            self.assertRegex(completed.stderr, r"links|reparse|junction")

    def test_required_source_entries_reject_symlinks(self) -> None:
        with temporary_area() as area:
            probe = area / "symlink-probe"
            try:
                os.symlink(SOURCE_ROOT / "README.md", probe)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"file symlink unavailable on this Windows host: {exc}")
            probe.unlink()

            cases = ("required-file", "skill-directory", "tests-directory")
            for case in cases:
                with self.subTest(case=case):
                    source = copy_source(area / f"source-{case}")
                    if case == "required-file":
                        original = source / "README.original"
                        (source / "README.md").replace(original)
                        os.symlink(original, source / "README.md")
                    elif case == "skill-directory":
                        name = "manage-workspace-memory"
                        original = source / f"{name}.original"
                        (source / name).replace(original)
                        os.symlink(original, source / name, target_is_directory=True)
                    else:
                        original = source / "tests.original"
                        (source / "tests").replace(original)
                        os.symlink(original, source / "tests", target_is_directory=True)
                    output_parent = area / f"output-{case}"
                    output_parent.mkdir()
                    target = output_parent / PLUGIN_NAME
                    completed = run_export(target, source=source)
                    self.assertEqual(completed.returncode, 2)
                    self.assertFalse(target.exists())
                    self.assertRegex(completed.stderr, r"links|reparse|junction")

    @unittest.skipUnless(os.name == "nt", "junction test is Windows-specific")
    def test_ignored_name_junction_is_audited_before_skip(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            external = area / "junction-target"
            external.mkdir()
            (external / "private.txt").write_text("private\n", encoding="utf-8")
            junction = source / "manage-workspace-memory" / ".GiT"
            created = subprocess.run(
                [
                    "cmd.exe",
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(junction),
                    str(external),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if created.returncode != 0:
                self.skipTest(f"junction unavailable: {created.stderr or created.stdout}")
            try:
                target = area / PLUGIN_NAME
                completed = run_export(target, source=source)
                self.assertEqual(completed.returncode, 2)
                self.assertFalse(target.exists())
                self.assertRegex(completed.stderr, r"links|reparse|junction")
            finally:
                if os.path.lexists(junction):
                    os.rmdir(junction)

    def test_required_root_hardlink_is_rejected(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            version = source / "VERSION"
            content = version.read_bytes()
            version.unlink()
            origin = area / "VERSION.origin"
            origin.write_bytes(content)
            try:
                os.link(origin, version)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"hard links unavailable on this filesystem: {exc}")
            target = area / PLUGIN_NAME
            completed = run_export(target, source=source)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())
            self.assertIn("hard-linked", completed.stderr)

    def test_internal_temporary_directory_names_are_casefolded_and_rejected(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            skill = source / "manage-workspace-memory"
            mixed_activation = skill / ".AcTiVaTiOn-secret"
            mixed_activation.mkdir()
            (mixed_activation / "audit.txt").write_text("internal\n", encoding="utf-8")
            target = area / PLUGIN_NAME
            completed = run_export(target, source=source)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())
            self.assertIn("internal temporary path", completed.stderr)

    def test_stale_release_runner_directory_is_rejected_not_copied(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            residue = source / "tests" / ".ReLeAsE-RuNnEr-stale"
            residue.mkdir()
            (residue / "evidence.txt").write_text("stale\n", encoding="utf-8")
            target = area / PLUGIN_NAME
            completed = run_export(target, source=source)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())
            self.assertIn("internal temporary path", completed.stderr)

    def test_internal_hardlink_is_rejected(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            victim = (
                source
                / "manage-workspace-memory"
                / "references"
                / "session-lifecycle.md"
            )
            original_bytes = victim.read_bytes()
            victim.unlink()
            origin = area / "hardlink-origin.md"
            origin.write_bytes(original_bytes)
            try:
                os.link(origin, victim)
            except (OSError, NotImplementedError) as exc:
                self.skipTest(f"hard links unavailable on this filesystem: {exc}")
            target = area / PLUGIN_NAME
            completed = run_export(target, source=source)
            self.assertEqual(completed.returncode, 2)
            self.assertFalse(target.exists())
            self.assertIn("hard-linked", completed.stderr)

    def test_assembly_plan_rejects_mutation_before_checksums(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            target = area / PLUGIN_NAME
            original_verify = EXPORTER_MODULE.verify_assembly_plan
            calls = 0

            def mutate_then_verify(root: Path, plan) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    (root / "README.md").write_bytes(b"assembly tamper\n")
                original_verify(root, plan)

            with mock.patch.object(
                EXPORTER_MODULE,
                "verify_assembly_plan",
                side_effect=mutate_then_verify,
            ):
                with self.assertRaisesRegex(
                    EXPORTER_MODULE.ExportError,
                    r"snapshot changed|bytes changed",
                ):
                    EXPORTER_MODULE.export(exporter_args(source, target))
            self.assertFalse(target.exists())
            self.assertEqual(list(area.glob(f".{PLUGIN_NAME}.staging-*")), [])
            self.assertEqual(list(area.glob(f".{PLUGIN_NAME}.owner-*")), [])

    def test_assembly_plan_rejects_unexpected_file_before_checksums(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            target = area / PLUGIN_NAME
            original_verify = EXPORTER_MODULE.verify_assembly_plan
            calls = 0

            def add_extra_then_verify(root: Path, plan) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    (root / "unexpected.txt").write_text(
                        "not planned\n", encoding="utf-8"
                    )
                original_verify(root, plan)

            with mock.patch.object(
                EXPORTER_MODULE,
                "verify_assembly_plan",
                side_effect=add_extra_then_verify,
            ):
                with self.assertRaisesRegex(
                    EXPORTER_MODULE.ExportError,
                    "extra=.*unexpected.txt",
                ):
                    EXPORTER_MODULE.export(exporter_args(source, target))
            self.assertFalse(target.exists())

    def test_same_identity_target_ancestor_is_rejected_as_physical_alias(self) -> None:
        with temporary_area() as area:
            source = area / "source"
            source.mkdir()
            source_identity = EXPORTER_MODULE.real_directory_identity(source)
            alias_parent = area / "lexically-separate"
            alias_parent.mkdir()
            target = alias_parent / PLUGIN_NAME
            original_identity = EXPORTER_MODULE.real_directory_identity

            def alias_identity(path: Path):
                if Path(path) == alias_parent:
                    return source_identity
                return original_identity(path)

            with mock.patch.object(
                EXPORTER_MODULE,
                "real_directory_identity",
                side_effect=alias_identity,
            ):
                with self.assertRaisesRegex(
                    EXPORTER_MODULE.ExportError,
                    "physically aliases",
                ):
                    EXPORTER_MODULE.validate_target(
                        source,
                        source_identity,
                        target,
                        PLUGIN_NAME,
                    )

    def test_published_candidate_is_rechecked_against_original_assembly_plan(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            target = area / PLUGIN_NAME
            original_publish = EXPORTER_MODULE.atomic_publish_no_replace

            def publish_then_mutate(staging: Path, destination: Path) -> None:
                original_publish(staging, destination)
                (destination / "README.md").write_bytes(b"post-publish tamper\n")

            with mock.patch.object(
                EXPORTER_MODULE,
                "atomic_publish_no_replace",
                side_effect=publish_then_mutate,
            ):
                with self.assertRaisesRegex(
                    EXPORTER_MODULE.ExportError,
                    r"snapshot changed|bytes changed",
                ):
                    EXPORTER_MODULE.export(exporter_args(source, target))
            self.assertEqual(
                (target / "README.md").read_bytes(),
                b"post-publish tamper\n",
            )
            self.assertEqual(list(area.glob(f".{PLUGIN_NAME}.owner-*")), [])

    def test_cleanup_failure_reports_owned_residual_paths(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            target = area / PLUGIN_NAME
            with mock.patch.object(
                EXPORTER_MODULE,
                "assemble_candidate",
                side_effect=EXPORTER_MODULE.ExportError("synthetic failure"),
            ), mock.patch.object(
                EXPORTER_MODULE.shutil,
                "rmtree",
                side_effect=PermissionError("synthetic cleanup denial"),
            ):
                with self.assertRaisesRegex(
                    EXPORTER_MODULE.ExportError,
                    r"cleanup failed:.*residual staging=.*marker=",
                ):
                    EXPORTER_MODULE.export(exporter_args(source, target))
            self.assertFalse(target.exists())
            self.assertEqual(
                len(list(area.glob(f".{PLUGIN_NAME}.staging-*"))),
                1,
            )
            self.assertEqual(
                len(list(area.glob(f".{PLUGIN_NAME}.owner-*"))),
                1,
            )

    def test_concurrent_target_appearance_is_rejected_and_preserved(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            target = area / PLUGIN_NAME
            original_publish = EXPORTER_MODULE.atomic_publish_no_replace

            def appear_then_publish(staging: Path, destination: Path) -> None:
                destination.mkdir()
                (destination / "attacker.txt").write_text(
                    "preserve\n", encoding="utf-8"
                )
                original_publish(staging, destination)

            with mock.patch.object(
                EXPORTER_MODULE,
                "atomic_publish_no_replace",
                side_effect=appear_then_publish,
            ):
                with self.assertRaisesRegex(
                    EXPORTER_MODULE.ExportError,
                    "concurrent|appeared",
                ):
                    EXPORTER_MODULE.export(exporter_args(source, target))
            self.assertEqual(
                (target / "attacker.txt").read_text(encoding="utf-8"),
                "preserve\n",
            )
            self.assertEqual(list(area.glob(f".{PLUGIN_NAME}.staging-*")), [])
            self.assertEqual(list(area.glob(f".{PLUGIN_NAME}.owner-*")), [])

    def test_target_replacement_after_publish_is_detected_and_never_deleted(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            target = area / PLUGIN_NAME
            captured_candidate = area / "captured-candidate"
            original_publish = EXPORTER_MODULE.atomic_publish_no_replace

            def replace_after_publish(staging: Path, destination: Path) -> None:
                original_publish(staging, destination)
                destination.replace(captured_candidate)
                destination.mkdir()
                (destination / "replacement.txt").write_text(
                    "do not delete\n", encoding="utf-8"
                )

            with mock.patch.object(
                EXPORTER_MODULE,
                "atomic_publish_no_replace",
                side_effect=replace_after_publish,
            ):
                with self.assertRaisesRegex(
                    EXPORTER_MODULE.ExportError,
                    "replaced",
                ):
                    EXPORTER_MODULE.export(exporter_args(source, target))
            self.assertEqual(
                (target / "replacement.txt").read_text(encoding="utf-8"),
                "do not delete\n",
            )
            self.assertTrue((captured_candidate / "SHA256SUMS").is_file())
            self.assertEqual(list(area.glob(f".{PLUGIN_NAME}.owner-*")), [])

    def test_cleanup_refuses_replaced_staging_identity(self) -> None:
        with temporary_area() as area:
            source = copy_source(area / "source")
            target = area / PLUGIN_NAME
            captured_staging = area / "captured-staging"

            def replace_staging(
                staging: Path,
                _plan,
                _plugin_manifest,
                _release_manifest,
            ) -> None:
                staging.replace(captured_staging)
                staging.mkdir()
                (staging / "replacement.txt").write_text(
                    "ownership changed\n", encoding="utf-8"
                )
                raise EXPORTER_MODULE.ExportError("synthetic assembly failure")

            with mock.patch.object(
                EXPORTER_MODULE,
                "assemble_candidate",
                side_effect=replace_staging,
            ):
                with self.assertRaisesRegex(
                    EXPORTER_MODULE.ExportError,
                    "synthetic assembly failure",
                ):
                    EXPORTER_MODULE.export(exporter_args(source, target))
            replacement_dirs = list(area.glob(f".{PLUGIN_NAME}.staging-*"))
            self.assertEqual(len(replacement_dirs), 1)
            self.assertEqual(
                (replacement_dirs[0] / "replacement.txt").read_text(encoding="utf-8"),
                "ownership changed\n",
            )
            self.assertTrue(captured_staging.is_dir())
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
