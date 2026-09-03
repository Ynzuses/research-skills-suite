"""Adversarial tests for the deterministic workspace bootstrap helper."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unicodedata
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Iterator
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1] / "manage-workspace-memory"
SCRIPT = SKILL_ROOT / "scripts" / "apply_workspace_bootstrap.py"
TEMPLATE = SKILL_ROOT / "assets" / "BOOTSTRAP_MANIFEST.json.template"
SCHEMA = SKILL_ROOT / "assets" / "BOOTSTRAP_MANIFEST.schema.json"
START_MARKER = "<!-- manage-workspace-memory:managed-block:start -->"
END_MARKER = "<!-- manage-workspace-memory:managed-block:end -->"


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def approved_manifest(
    *,
    directories: list[str] | None = None,
    files: list[tuple[str, str, str]] | None = None,
    entry_path: str = "AGENTS.md",
    entry_content: str = "# Workspace memory route\n\nUse the verified status entry.",
    create_entry: bool = False,
    entry_operation: str = "merge",
    previous_managed_block_sha256: str | None = None,
    frozen_paths: list[str] | None = None,
) -> dict[str, Any]:
    rendered_files = []
    for path, role, content in files or []:
        rendered_files.append(
            {
                "path": path,
                "role": role,
                "content": content,
                "content_sha256": digest_text(content),
            }
        )
    return {
        "schema_version": 1,
        "approval": {
            "state": "approved",
            "decision_id": "decision:workspace-bootstrap:v1",
            "approved_by_role": "workspace-owner",
            "approved_at": "2026-08-20T12:00:00+08:00",
            "manifest_sha256": None,
        },
        "workspace": {
            "root": ".",
            "root_identity": {
                "normalized_path_sha256": None,
                "device": None,
                "inode": None,
            },
            "frozen_inventory_complete": True,
            "frozen_paths": frozen_paths or [],
        },
        "directories": directories or [],
        "files": rendered_files,
        "entry": {
            "path": entry_path,
            "create_if_missing": create_entry,
            "operation": entry_operation,
            "previous_managed_block_sha256": previous_managed_block_sha256,
            "managed_block_id": "manage-workspace-memory-v1",
            "content": entry_content,
            "content_sha256": digest_text(entry_content),
        },
    }


def bind_approved_manifest(root: Path, manifest: dict[str, Any]) -> None:
    root = root.resolve(strict=True)
    info = os.stat(root, follow_symlinks=False)
    normalized = os.path.normcase(os.path.normpath(str(root))).replace("\\", "/")
    normalized = unicodedata.normalize("NFC", normalized)
    manifest["workspace"]["root_identity"] = {
        "normalized_path_sha256": digest_text(normalized),
        "device": int(info.st_dev),
        "inode": int(info.st_ino),
    }


def rehash_approved_manifest(manifest: dict[str, Any]) -> None:
    manifest["approval"]["manifest_sha256"] = None
    canonical = json.dumps(
        manifest,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    manifest["approval"]["manifest_sha256"] = digest_text(canonical)


def write_manifest(
    path: Path,
    manifest: dict[str, Any],
    *,
    root: Path | None = None,
    bind: bool = True,
) -> None:
    if manifest.get("approval", {}).get("state") == "approved" and bind:
        if root is None:
            raise AssertionError("approved test manifests require an explicit root")
        bind_approved_manifest(root, manifest)
        rehash_approved_manifest(manifest)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        errors="strict",
    )


def load_helper_module() -> Any:
    module_name = f"test_apply_workspace_bootstrap_{os.getpid()}_{id(object())}"
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load bootstrap helper module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def invoke_module_main(module: Any, arguments: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        return_code = module.main(arguments)
    return return_code, stdout.getvalue(), stderr.getvalue()


def tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes], ...]:
    result: list[tuple[str, str, bytes]] = []
    for path in sorted(
        root.rglob("*"), key=lambda item: (item.as_posix().casefold(), item.as_posix())
    ):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result.append((relative, "symlink", os.readlink(path).encode("utf-8")))
        elif path.is_dir():
            result.append((relative, "directory", b""))
        else:
            result.append((relative, "file", path.read_bytes()))
    return tuple(result)


def run_helper(
    root: Path,
    manifest: Path,
    *,
    apply: bool = False,
    expected_plan_sha256: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "--root",
        str(root),
        "--manifest",
        str(manifest),
    ]
    if apply:
        command.append("--apply")
    if expected_plan_sha256 is not None:
        command.extend(["--expected-plan-sha256", expected_plan_sha256])
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONUTF8"] = "0"
    environment["PYTHONIOENCODING"] = "cp936"
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=environment,
    )


def inspect_root(root: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONUTF8"] = "0"
    environment["PYTHONIOENCODING"] = "cp936"
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--inspect-root"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=environment,
    )


@contextmanager
def isolated_case(prefix: str) -> Iterator[tuple[Path, Path, Path]]:
    with tempfile.TemporaryDirectory(prefix=prefix) as temporary:
        base = Path(temporary)
        root = base / "工作区 根"
        root.mkdir()
        yield base, root, base / "approved manifest.json"


class WorkspaceBootstrapTests(unittest.TestCase):
    def test_pending_template_and_schema_are_valid_safe_json(self) -> None:
        template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(template["approval"]["state"], "pending")
        self.assertIsNone(template["approval"]["manifest_sha256"])
        self.assertFalse(template["workspace"]["frozen_inventory_complete"])
        self.assertTrue(
            all(value is None for value in template["workspace"]["root_identity"].values())
        )
        self.assertEqual(template["directories"], [])
        self.assertEqual(template["files"], [])
        self.assertIsNone(template["entry"]["path"])
        self.assertFalse(template["entry"]["create_if_missing"])
        self.assertEqual(template["entry"]["operation"], "merge")
        self.assertIsNone(template["entry"]["previous_managed_block_sha256"])
        self.assertFalse(schema["additionalProperties"])

    def test_default_dry_run_is_byte_non_mutating_with_chinese_space_path(self) -> None:
        with isolated_case("bootstrap dry run ") as (_base, root, manifest_path):
            original = "# Existing instructions\n\nKeep this user rule.\n".encode("utf-8")
            (root / "AGENTS.md").write_bytes(original)
            manifest = approved_manifest(
                directories=["控制 面"],
                files=[
                    (
                        "控制 面/STATUS.md",
                        "current_status",
                        "# Current Status\n\nVerified locally.\n",
                    )
                ],
            )
            write_manifest(manifest_path, manifest, root=root)
            before = tree_snapshot(root)

            completed = run_helper(root, manifest_path)

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertEqual(tree_snapshot(root), before)
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["applied"])
            self.assertEqual(payload["mode"], "dry-run")
            self.assertEqual(payload["change_count"], 3)
            self.assertRegex(payload["plan_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                payload["approval"]["manifest_sha256"],
                manifest["approval"]["manifest_sha256"],
            )
            entry = next(item for item in payload["changes"] if item["kind"] == "entry")
            self.assertEqual(entry["pre_sha256"], hashlib.sha256(original).hexdigest())
            self.assertIsNotNone(entry["planned_post_sha256"])
            self.assertIsNone(entry["observed_post_sha256"])

    def test_apply_preserves_lf_or_crlf_entry_and_rerun_is_byte_idempotent(self) -> None:
        for newline in (b"\n", b"\r\n"):
            with (
                self.subTest(newline=newline),
                isolated_case("bootstrap newline ") as (_base, root, manifest_path),
            ):
                original = newline.join(
                    (b"# Existing instructions", b"", "原有规则。".encode("utf-8"), b"")
                )
                (root / "AGENTS.md").write_bytes(original)
                status_content = "# Current Status\n\n- State: verified\n"
                write_manifest(
                    manifest_path,
                    approved_manifest(
                        directories=["控制 面"],
                        files=[
                            (
                                "控制 面/STATUS.md",
                                "current_status",
                                status_content,
                            )
                        ],
                    ),
                    root=root,
                )

                dry_run = run_helper(root, manifest_path)
                self.assertEqual(dry_run.returncode, 0, dry_run.stderr or dry_run.stdout)
                reviewed_plan_sha256 = json.loads(dry_run.stdout)["plan_sha256"]

                first = run_helper(
                    root,
                    manifest_path,
                    apply=True,
                    expected_plan_sha256=reviewed_plan_sha256,
                )

                self.assertEqual(first.returncode, 0, first.stderr or first.stdout)
                entry_bytes = (root / "AGENTS.md").read_bytes()
                self.assertTrue(entry_bytes.startswith(original))
                self.assertEqual(entry_bytes.count(START_MARKER.encode("ascii")), 1)
                self.assertEqual(entry_bytes.count(END_MARKER.encode("ascii")), 1)
                if newline == b"\r\n":
                    self.assertNotIn(b"\n", entry_bytes.replace(b"\r\n", b""))
                else:
                    self.assertNotIn(b"\r", entry_bytes)
                self.assertEqual(
                    (root / "控制 面" / "STATUS.md").read_text(encoding="utf-8"),
                    status_content,
                )
                first_payload = json.loads(first.stdout)
                entry_change = next(
                    item for item in first_payload["changes"] if item["kind"] == "entry"
                )
                self.assertEqual(
                    entry_change["planned_post_sha256"],
                    entry_change["observed_post_sha256"],
                )
                after_first = tree_snapshot(root)

                second = run_helper(root, manifest_path, apply=True)

                self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
                self.assertEqual(tree_snapshot(root), after_first)
                second_payload = json.loads(second.stdout)
                self.assertEqual(second_payload["change_count"], 0)
                self.assertTrue(
                    all(
                        item["state"] in {"existing", "unchanged"}
                        for item in second_payload["changes"]
                    )
                )

    def test_pending_approval_is_rejected_without_writes(self) -> None:
        with isolated_case("bootstrap pending ") as (_base, root, manifest_path):
            manifest = json.loads(TEMPLATE.read_text(encoding="utf-8"))
            write_manifest(manifest_path, manifest)
            before = tree_snapshot(root)

            completed = run_helper(root, manifest_path, apply=True)

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(tree_snapshot(root), before)
            payload = json.loads(completed.stderr)
            self.assertEqual(payload["error_kind"], "manifest")
            self.assertIn("not 'approved'", payload["error"])

    def test_existing_file_conflict_stops_before_any_write(self) -> None:
        with isolated_case("bootstrap conflict ") as (_base, root, manifest_path):
            (root / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
            control = root / "control"
            control.mkdir()
            (control / "STATUS.md").write_text("user-owned\n", encoding="utf-8")
            write_manifest(
                manifest_path,
                approved_manifest(
                    directories=["control", "new-area"],
                    files=[
                        ("control/STATUS.md", "current_status", "approved\n"),
                        ("new-area/MEMORY.md", "long_term_memory", "new\n"),
                    ],
                ),
                root=root,
            )
            before = tree_snapshot(root)

            completed = run_helper(root, manifest_path, apply=True)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(tree_snapshot(root), before)
            payload = json.loads(completed.stderr)
            self.assertEqual(payload["error_kind"], "conflict")
            self.assertIn("not byte-identical", payload["error"])

    def test_ambiguous_or_different_managed_block_is_a_conflict(self) -> None:
        cases = {
            "different": (f"# Existing\n\n{START_MARKER}\nDifferent content.\n{END_MARKER}\n"),
            "partial": f"# Existing\n\n{START_MARKER}\n",
            "repeated": (f"{START_MARKER}\nA\n{END_MARKER}\n{START_MARKER}\nA\n{END_MARKER}\n"),
            "embedded": (
                f"# Existing {START_MARKER}\n"
                "# Workspace memory route\n\nUse the verified status entry.\n"
                f"{END_MARKER} trailing\n"
            ),
        }
        for name, entry_text in cases.items():
            with (
                self.subTest(name=name),
                isolated_case("bootstrap marker ") as (_base, root, manifest_path),
            ):
                (root / "AGENTS.md").write_text(entry_text, encoding="utf-8")
                write_manifest(manifest_path, approved_manifest(), root=root)
                before = tree_snapshot(root)

                completed = run_helper(root, manifest_path, apply=True)

                self.assertEqual(completed.returncode, 1)
                self.assertEqual(tree_snapshot(root), before)
                self.assertEqual(json.loads(completed.stderr)["error_kind"], "conflict")

    def test_escape_forbidden_and_undeclared_parent_paths_are_rejected(self) -> None:
        cases = (
            ("../outside.md", [], "parent traversal"),
            ("C" + ":/outside.md", [], "repository-relative"),
            (".git/hooks/setup.md", [".git", ".git/hooks"], "forbidden"),
            ("missing/STATUS.md", [], "not declared"),
        )
        for target, directories, message in cases:
            with (
                self.subTest(target=target),
                isolated_case("bootstrap path ") as (base, root, manifest_path),
            ):
                (root / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
                outside = base / "outside.md"
                outside.write_text("outside\n", encoding="utf-8")
                write_manifest(
                    manifest_path,
                    approved_manifest(
                        directories=directories,
                        files=[(target, "current_status", "approved\n")],
                    ),
                    root=root,
                )
                before = tree_snapshot(root)

                completed = run_helper(root, manifest_path, apply=True)

                self.assertIn(completed.returncode, {1, 2})
                self.assertEqual(tree_snapshot(root), before)
                self.assertEqual(outside.read_text(encoding="utf-8"), "outside\n")
                self.assertIn(message, json.loads(completed.stderr)["error"])

    def test_frozen_target_and_missing_entry_authority_stop_before_writes(self) -> None:
        for case in ("frozen", "missing-entry"):
            with (
                self.subTest(case=case),
                isolated_case("bootstrap boundary ") as (_base, root, manifest_path),
            ):
                if case == "frozen":
                    (root / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
                    (root / "archive").mkdir()
                    manifest = approved_manifest(
                        directories=["new-control"],
                        files=[("archive/STATUS.md", "current_status", "approved\n")],
                        frozen_paths=["archive"],
                    )
                else:
                    manifest = approved_manifest(create_entry=False)
                write_manifest(manifest_path, manifest, root=root)
                before = tree_snapshot(root)

                completed = run_helper(root, manifest_path, apply=True)

                self.assertEqual(completed.returncode, 1)
                self.assertEqual(tree_snapshot(root), before)
                error = json.loads(completed.stderr)["error"]
                self.assertIn("frozen" if case == "frozen" else "create_if_missing", error)

    def test_symlink_component_is_rejected_when_supported(self) -> None:
        with isolated_case("bootstrap symlink ") as (base, root, manifest_path):
            (root / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
            outside = base / "outside"
            outside.mkdir()
            link = root / "linked"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlink unavailable: {exc}")
            write_manifest(
                manifest_path,
                approved_manifest(files=[("linked/STATUS.md", "current_status", "approved\n")]),
                root=root,
            )
            before = tree_snapshot(root)

            completed = run_helper(root, manifest_path, apply=True)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(tree_snapshot(root), before)
            self.assertEqual(list(outside.iterdir()), [])
            self.assertIn("symbolic-link", json.loads(completed.stderr)["error"])

    def test_manifest_hash_and_normalized_root_identity_are_approval_bound(self) -> None:
        for case in ("manifest", "root"):
            with (
                self.subTest(case=case),
                isolated_case("bootstrap approval binding ") as (_base, root, manifest_path),
            ):
                entry = root / "AGENTS.md"
                entry.write_text("# Existing\n", encoding="utf-8")
                manifest = approved_manifest()
                bind_approved_manifest(root, manifest)
                rehash_approved_manifest(manifest)
                if case == "manifest":
                    changed = "# Changed approved route\n"
                    manifest["entry"]["content"] = changed
                    manifest["entry"]["content_sha256"] = digest_text(changed)
                else:
                    manifest["workspace"]["root_identity"]["inode"] += 1
                    rehash_approved_manifest(manifest)
                write_manifest(manifest_path, manifest, bind=False)
                before = tree_snapshot(root)

                completed = run_helper(root, manifest_path, apply=True)

                self.assertEqual(completed.returncode, 2)
                self.assertEqual(tree_snapshot(root), before)
                error = json.loads(completed.stderr)
                self.assertEqual(error["error_kind"], "manifest")
                self.assertFalse(error["writes_started"])
                self.assertIn(
                    "manifest_sha256" if case == "manifest" else "root identity",
                    error["error"],
                )

    def test_inspect_root_reports_exact_approval_identity_without_manifest(self) -> None:
        with isolated_case("bootstrap root identity ") as (_base, root, _manifest_path):
            completed = inspect_root(root)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            manifest = approved_manifest()
            bind_approved_manifest(root, manifest)
            self.assertEqual(
                payload["root_identity"],
                manifest["workspace"]["root_identity"],
            )

    def test_reviewed_plan_hash_rejects_same_byte_entry_inode_swap(self) -> None:
        with isolated_case("bootstrap plan identity ") as (_base, root, manifest_path):
            entry = root / "AGENTS.md"
            original = b"# Existing\n"
            entry.write_bytes(original)
            manifest = approved_manifest()
            write_manifest(manifest_path, manifest, root=root)

            dry_run = run_helper(root, manifest_path)
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr or dry_run.stdout)
            reviewed_plan = json.loads(dry_run.stdout)["plan_sha256"]
            previous_identity = os.stat(entry, follow_symlinks=False).st_ino
            replacement = root / "same-bytes replacement.md"
            replacement.write_bytes(original)
            os.replace(replacement, entry)
            self.assertNotEqual(
                os.stat(entry, follow_symlinks=False).st_ino,
                previous_identity,
            )

            completed = run_helper(
                root,
                manifest_path,
                apply=True,
                expected_plan_sha256=reviewed_plan,
            )

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(entry.read_bytes(), original)
            payload = json.loads(completed.stderr)
            self.assertIn("plan hash differs", payload["error"])
            self.assertFalse(payload["writes_started"])

    def test_existing_hard_link_target_is_rejected_before_write(self) -> None:
        with isolated_case("bootstrap hard link ") as (_base, root, manifest_path):
            entry = root / "AGENTS.md"
            alias = root / "AGENTS.alias.md"
            original = b"# Existing\n"
            entry.write_bytes(original)
            try:
                os.link(entry, alias)
            except OSError as exc:
                self.skipTest(f"hard links unavailable: {exc}")
            write_manifest(manifest_path, approved_manifest(), root=root)
            before = tree_snapshot(root)

            completed = run_helper(root, manifest_path, apply=True)

            self.assertEqual(completed.returncode, 1)
            self.assertEqual(tree_snapshot(root), before)
            self.assertEqual(entry.read_bytes(), original)
            self.assertEqual(alias.read_bytes(), original)
            payload = json.loads(completed.stderr)
            self.assertIn("link count", payload["error"])
            self.assertFalse(payload["writes_started"])

    @unittest.skipUnless(os.name == "nt", "Windows junction test")
    def test_windows_junction_or_reparse_parent_is_rejected(self) -> None:
        with isolated_case("bootstrap junction ") as (base, root, manifest_path):
            (root / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
            outside = base / "outside"
            outside.mkdir()
            junction = root / "junction"
            command_processor = os.environ.get("COMSPEC")
            if not command_processor:
                self.skipTest("COMSPEC is unavailable")
            created = subprocess.run(
                [
                    command_processor,
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(junction),
                    str(outside),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if created.returncode != 0 or not os.path.lexists(junction):
                self.skipTest("junction creation is unavailable")
            try:
                write_manifest(
                    manifest_path,
                    approved_manifest(
                        files=[("junction/STATUS.md", "current_status", "approved\n")]
                    ),
                    root=root,
                )

                completed = run_helper(root, manifest_path, apply=True)

                self.assertEqual(completed.returncode, 1)
                self.assertEqual(list(outside.iterdir()), [])
                self.assertRegex(
                    json.loads(completed.stderr)["error"],
                    r"junction|reparse",
                )
            finally:
                if os.path.lexists(junction):
                    os.rmdir(junction)

    def test_entry_and_parent_inode_swaps_after_preflight_are_rejected(self) -> None:
        for case in ("entry", "parent"):
            with (
                self.subTest(case=case),
                isolated_case("bootstrap toctou ") as (_base, root, manifest_path),
            ):
                entry = root / "AGENTS.md"
                entry.write_bytes(b"# Existing\n")
                if case == "parent":
                    control = root / "control"
                    control.mkdir()
                    manifest = approved_manifest(
                        files=[("control/STATUS.md", "current_status", "approved\n")],
                    )
                else:
                    manifest = approved_manifest()
                write_manifest(manifest_path, manifest, root=root)
                module = load_helper_module()
                original_apply = module.apply_plan

                def swap_then_apply(
                    root_argument: Path,
                    manifest_path_argument: Path,
                    parsed_manifest: Any,
                    changes: list[Any],
                    recovery_items: list[Any],
                ) -> None:
                    if case == "entry":
                        replacement = root / "same entry bytes.md"
                        replacement.write_bytes(entry.read_bytes())
                        os.replace(replacement, entry)
                    else:
                        old_parent = root / "control previous"
                        os.replace(root / "control", old_parent)
                        (root / "control").mkdir()
                    original_apply(
                        root_argument,
                        manifest_path_argument,
                        parsed_manifest,
                        changes,
                        recovery_items,
                    )

                with mock.patch.object(module, "apply_plan", side_effect=swap_then_apply):
                    return_code, _stdout, stderr = invoke_module_main(
                        module,
                        [
                            "--root",
                            str(root),
                            "--manifest",
                            str(manifest_path),
                            "--apply",
                        ],
                    )

                self.assertEqual(return_code, 1)
                payload = json.loads(stderr)
                self.assertRegex(payload["error"], r"identity changed")
                self.assertFalse(payload["writes_started"])
                self.assertNotIn(START_MARKER.encode("ascii"), entry.read_bytes())
                if case == "parent":
                    self.assertFalse((root / "control" / "STATUS.md").exists())

    def test_partial_apply_error_reports_persisted_and_recovery_manifest(self) -> None:
        with isolated_case("bootstrap partial apply ") as (_base, root, manifest_path):
            entry = root / "AGENTS.md"
            entry.write_text("# Existing\n", encoding="utf-8")
            manifest = approved_manifest(
                files=[
                    ("A.md", "current_status", "A\n"),
                    ("B.md", "asset_index", "B\n"),
                ]
            )
            write_manifest(manifest_path, manifest, root=root)
            module = load_helper_module()
            original_write = module.write_new_file
            calls = 0

            def fail_second_write(*arguments: Any) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise module.ApplyError("injected second-write failure")
                original_write(*arguments)

            with mock.patch.object(module, "write_new_file", side_effect=fail_second_write):
                return_code, _stdout, stderr = invoke_module_main(
                    module,
                    [
                        "--root",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--apply",
                    ],
                )

            self.assertEqual(return_code, 1)
            payload = json.loads(stderr)
            self.assertTrue(payload["writes_started"])
            self.assertEqual(
                [item["path"] for item in payload["persisted_changes"]],
                ["A.md"],
            )
            self.assertTrue(any(item["path"] == "A.md" for item in payload["recovery_required"]))
            self.assertEqual((root / "A.md").read_bytes(), b"A\n")
            self.assertFalse((root / "B.md").exists())
            self.assertNotIn(START_MARKER.encode("ascii"), entry.read_bytes())

            recovered = run_helper(root, manifest_path, apply=True)
            self.assertEqual(recovered.returncode, 0, recovered.stderr or recovered.stdout)
            after_recovery = tree_snapshot(root)
            repeated = run_helper(root, manifest_path, apply=True)
            self.assertEqual(repeated.returncode, 0, repeated.stderr or repeated.stdout)
            self.assertEqual(tree_snapshot(root), after_recovery)
            self.assertEqual(json.loads(repeated.stdout)["change_count"], 0)

    def test_newly_created_parent_swap_is_detected_before_child_write(self) -> None:
        with isolated_case("bootstrap created parent swap ") as (
            _base,
            root,
            manifest_path,
        ):
            (root / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
            manifest = approved_manifest(
                directories=["new-control"],
                files=[("new-control/STATUS.md", "current_status", "approved\n")],
            )
            write_manifest(manifest_path, manifest, root=root)
            module = load_helper_module()
            original_bind = module.bind_post_creation_parent_chains

            def swap_then_bind(root_argument: Path, changes: list[Any]) -> None:
                os.replace(
                    root / "new-control",
                    root / "new-control original",
                )
                (root / "new-control").mkdir()
                original_bind(root_argument, changes)

            with mock.patch.object(
                module,
                "bind_post_creation_parent_chains",
                side_effect=swap_then_bind,
            ):
                return_code, _stdout, stderr = invoke_module_main(
                    module,
                    [
                        "--root",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--apply",
                    ],
                )

            self.assertEqual(return_code, 1)
            payload = json.loads(stderr)
            self.assertIn("declared parent directory identity changed", payload["error"])
            self.assertTrue(payload["writes_started"])
            self.assertEqual(
                [item["path"] for item in payload["persisted_changes"]],
                ["new-control"],
            )
            self.assertFalse((root / "new-control" / "STATUS.md").exists())

    def test_manifest_cannot_be_the_entry_physical_file(self) -> None:
        with isolated_case("bootstrap manifest alias ") as (_base, root, _manifest_path):
            manifest_path = root / "approved-manifest.md"
            manifest = approved_manifest(entry_path="approved-manifest.md")
            write_manifest(manifest_path, manifest, root=root)
            before = tree_snapshot(root)

            completed = run_helper(root, manifest_path, apply=True)

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(tree_snapshot(root), before)
            payload = json.loads(completed.stderr)
            self.assertEqual(payload["error_kind"], "manifest")
            self.assertIn("same physical file", payload["error"])
            self.assertFalse(payload["writes_started"])

    def test_controlled_managed_block_update_binds_old_hash_and_is_idempotent(self) -> None:
        with isolated_case("bootstrap managed update ") as (_base, root, manifest_path):
            old_content = "# Old route\n\nRead STATUS.md."
            new_content = "# New route\n\nRead MEMORY.md, then STATUS.md."
            entry = root / "AGENTS.md"
            entry.write_text(
                f"# User rules\n\n{START_MARKER}\n{old_content}\n{END_MARKER}\n",
                encoding="utf-8",
            )
            rendered = entry.read_bytes()
            block_start = rendered.index(START_MARKER.encode("ascii"))
            block_end = rendered.index(END_MARKER.encode("ascii"), block_start)
            block_end += len(END_MARKER)
            old_block = rendered[block_start:block_end]

            wrong = approved_manifest(
                entry_content=new_content,
                entry_operation="update",
                previous_managed_block_sha256="0" * 64,
            )
            write_manifest(manifest_path, wrong, root=root)
            before = entry.read_bytes()
            rejected = run_helper(root, manifest_path, apply=True)
            self.assertEqual(rejected.returncode, 1)
            self.assertEqual(entry.read_bytes(), before)
            self.assertIn("previous managed-block SHA-256", json.loads(rejected.stderr)["error"])

            approved = approved_manifest(
                entry_content=new_content,
                entry_operation="update",
                previous_managed_block_sha256=hashlib.sha256(old_block).hexdigest(),
            )
            write_manifest(manifest_path, approved, root=root)
            dry_run = run_helper(root, manifest_path)
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr or dry_run.stdout)
            plan_hash = json.loads(dry_run.stdout)["plan_sha256"]
            applied = run_helper(
                root,
                manifest_path,
                apply=True,
                expected_plan_sha256=plan_hash,
            )
            self.assertEqual(applied.returncode, 0, applied.stderr or applied.stdout)
            updated = entry.read_bytes()
            newline = "\r\n" if b"\r\n" in updated else "\n"
            self.assertIn(
                new_content.replace("\n", newline).encode("utf-8"),
                updated,
            )
            self.assertNotIn(
                old_content.replace("\n", newline).encode("utf-8"),
                updated,
            )

            after = tree_snapshot(root)
            repeated = run_helper(root, manifest_path, apply=True)
            self.assertEqual(repeated.returncode, 0, repeated.stderr or repeated.stdout)
            self.assertEqual(tree_snapshot(root), after)
            self.assertEqual(json.loads(repeated.stdout)["change_count"], 0)

    def test_final_window_concurrent_entry_is_retained_as_recovery_backup(self) -> None:
        with isolated_case("bootstrap concurrent replace ") as (_base, root, manifest_path):
            entry = root / "AGENTS.md"
            entry.write_bytes(b"# Existing\n")
            write_manifest(manifest_path, approved_manifest(), root=root)
            module = load_helper_module()
            original_exchange = module.atomic_recoverable_exchange
            concurrent = b"# Concurrent writer\n"

            def swap_then_exchange(
                root_argument: Path,
                target: Path,
                replacement: Path,
                recovery_items: list[Any],
            ) -> Path:
                competing = root / "competing-entry.md"
                competing.write_bytes(concurrent)
                os.replace(competing, target)
                return original_exchange(root_argument, target, replacement, recovery_items)

            with mock.patch.object(
                module,
                "atomic_recoverable_exchange",
                side_effect=swap_then_exchange,
            ):
                return_code, _stdout, stderr = invoke_module_main(
                    module,
                    [
                        "--root",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--apply",
                    ],
                )

            self.assertEqual(return_code, 1)
            payload = json.loads(stderr)
            self.assertIn("final replacement window", payload["error"])
            backups = [
                item
                for item in payload["recovery_required"]
                if item["kind"] == "replacement_backup"
            ]
            self.assertEqual(len(backups), 1)
            backup = Path(backups[0]["actual_path"])
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_bytes(), concurrent)
            self.assertEqual(backups[0]["sha256"], hashlib.sha256(concurrent).hexdigest())

    def test_parent_swap_after_open_reports_actual_landed_file(self) -> None:
        with isolated_case("bootstrap landed path ") as (_base, root, manifest_path):
            (root / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
            (root / "control").mkdir()
            write_manifest(
                manifest_path,
                approved_manifest(
                    files=[("control/STATUS.md", "current_status", "approved\n")]
                ),
                root=root,
            )
            module = load_helper_module()
            original_write_all = module.write_all
            swapped = False
            swap_error: OSError | None = None

            def swap_parent_during_write(descriptor: int, payload: bytes) -> None:
                nonlocal swapped, swap_error
                if not swapped and payload == b"approved\n":
                    swapped = True
                    try:
                        os.replace(root / "control", root / "control-displaced")
                    except OSError as exc:
                        swap_error = exc
                        original_write_all(descriptor, payload)
                        return
                    (root / "control").mkdir()
                original_write_all(descriptor, payload)

            with mock.patch.object(module, "write_all", side_effect=swap_parent_during_write):
                return_code, _stdout, stderr = invoke_module_main(
                    module,
                    [
                        "--root",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--apply",
                    ],
                )

            if swap_error is not None:
                self.skipTest(
                    "parent rename while a child file is open is unavailable on this "
                    f"Windows/filesystem combination: {swap_error}"
                )
            self.assertEqual(return_code, 1)
            payload = json.loads(stderr)
            landed = [
                item
                for item in payload["recovery_required"]
                if item["kind"] == "opened_creation"
            ]
            self.assertEqual(len(landed), 1)
            self.assertIn("control-displaced", landed[0]["actual_path"])
            self.assertEqual((root / "control-displaced" / "STATUS.md").read_bytes(), b"approved\n")
            self.assertFalse((root / "control" / "STATUS.md").exists())

    def test_failed_recoverable_exchange_reports_retained_exclusive_temp(self) -> None:
        with isolated_case("bootstrap replace failure ") as (_base, root, manifest_path):
            entry = root / "AGENTS.md"
            original = b"# Existing\n"
            entry.write_bytes(original)
            write_manifest(manifest_path, approved_manifest(), root=root)
            module = load_helper_module()

            with mock.patch.object(
                module,
                "atomic_recoverable_exchange",
                side_effect=module.ApplyError("injected recoverable exchange failure"),
            ):
                return_code, _stdout, stderr = invoke_module_main(
                    module,
                    [
                        "--root",
                        str(root),
                        "--manifest",
                        str(manifest_path),
                        "--apply",
                    ],
                )

            self.assertEqual(return_code, 1)
            self.assertEqual(entry.read_bytes(), original)
            temporary_files = list(root.glob(".AGENTS.md.manage-workspace-memory-*.tmp"))
            self.assertEqual(len(temporary_files), 1)
            payload = json.loads(stderr)
            self.assertTrue(payload["writes_started"])
            self.assertEqual(payload["persisted_changes"], [])
            self.assertTrue(
                any(item["kind"] == "exclusive_temp" for item in payload["recovery_required"])
            )

    def test_helper_has_no_external_process_network_or_destructive_calls(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
        parents: dict[ast.AST, ast.AST] = {
            child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)
        }
        imported_roots: set[str] = set()
        called_attributes: set[str] = set()
        unlink_call_owners: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                called_attributes.add(node.func.attr)
                if node.func.attr == "unlink":
                    ancestor: ast.AST | None = node
                    while ancestor in parents and not isinstance(ancestor, ast.FunctionDef):
                        ancestor = parents[ancestor]
                    if isinstance(ancestor, ast.FunctionDef):
                        unlink_call_owners.add(ancestor.name)
        self.assertTrue(
            imported_roots.isdisjoint(
                {"asyncio", "ftplib", "http", "requests", "socket", "subprocess", "urllib"}
            )
        )
        self.assertTrue(
            called_attributes.isdisjoint(
                {"popen", "remove", "rename", "rmdir", "spawn", "system"}
            )
        )
        self.assertEqual(
            unlink_call_owners,
            {"reserve_vacant_backup_path", "delete_verified_backup"},
        )


if __name__ == "__main__":
    unittest.main()
