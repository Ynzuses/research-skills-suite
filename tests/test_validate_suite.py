"""Adversarial tests for the dependency-free static suite validator."""

from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SOURCE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = SOURCE_ROOT.parent
VALIDATOR = SOURCE_ROOT / "tests" / "validate_suite.py"


def ignore_copy(_directory: str, names: list[str]) -> set[str]:
    ignored = {
        name
        for name in names
        if name in {
            ".git",
            ".cache",
            ".venv",
            "__pycache__",
            "cache",
            "venv",
        }
        or name.startswith((".activation-", ".test-"))
        or name.endswith((".pyc", ".pyo"))
    }
    return ignored


@contextmanager
def cloned_source() -> Iterator[tuple[Path, Path]]:
    base = WORKSPACE_ROOT / f".skill-validator-test-{uuid.uuid4().hex}"
    root = base / "suite"
    base.mkdir(parents=False, exist_ok=False)
    try:
        shutil.copytree(SOURCE_ROOT, root, ignore=ignore_copy)
        yield base, root
    finally:
        shutil.rmtree(base)


def validate(root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--root",
            str(root),
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )


class ValidateSuiteTests(unittest.TestCase):
    def test_real_flat_source_is_static_pass(self) -> None:
        completed = validate(SOURCE_ROOT)
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        self.assertIn("RESULT: STATIC PASS", completed.stdout)
        self.assertIn("layout=flat-source", completed.stdout)
        self.assertNotIn("RELEASE PASS", completed.stdout)

    def test_supported_optional_frontmatter_is_accepted(self) -> None:
        with cloned_source() as (_base, root):
            skill = root / "evidence-traceable-literature-review" / "SKILL.md"
            text = skill.read_text(encoding="utf-8")
            text = text.replace(
                "\nmetadata:\n",
                "\nmetadata:\n  maturity: stable\n",
                1,
            )
            skill.write_text(text, encoding="utf-8", newline="\n")
            completed = validate(root)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr or completed.stdout,
            )

    def test_exact_skill_set_rejects_a_ninth_skill(self) -> None:
        with cloned_source() as (_base, root):
            extra = root / "undeclared-ninth-skill"
            extra.mkdir()
            (extra / "SKILL.md").write_text(
                "---\nname: undeclared-ninth-skill\n"
                "description: This should not enter the suite.\n---\n",
                encoding="utf-8",
            )
            completed = validate(root)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("exactly 4 declared Skills", completed.stdout)

    def test_commented_openai_fields_cannot_spoof_policy(self) -> None:
        with cloned_source() as (_base, root):
            agent = (
                root
                / "evidence-traceable-literature-review"
                / "agents"
                / "openai.yaml"
            )
            agent.write_text(
                "# interface:\n"
                "#   display_name: fake\n"
                "#   short_description: fake\n"
                "#   default_prompt: fake\n"
                "policy:\n"
                "  # allow_implicit_invocation: true\n"
                "  allow_implicit_invocation: false\n",
                encoding="utf-8",
                newline="\n",
            )
            completed = validate(root)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("missing interface.display_name", completed.stdout)
            self.assertIn("actual boolean true", completed.stdout)

    def test_existing_markdown_link_cannot_escape_repository(self) -> None:
        with cloned_source() as (base, root):
            (base / "outside.md").write_text("outside\n", encoding="utf-8")
            with (root / "README.md").open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n[escape](../outside.md)\n")
            completed = validate(root)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("local link escapes repository root", completed.stdout)

    def test_invalid_utf8_fails_stably_without_traceback(self) -> None:
        with cloned_source() as (_base, root):
            (root / "乱码.md").write_bytes(b"\xff\xfe")
            completed = validate(root)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("invalid UTF-8", completed.stdout)
            self.assertNotIn("Traceback", completed.stdout + completed.stderr)

    def test_binary_token_and_sensitive_name_are_rejected(self) -> None:
        with cloned_source() as (_base, root):
            (root / "opaque.blob").write_bytes(b"\x00\x01\x02")
            token = "API_" + "KEY=" + ("a" * 24)
            with (root / "LICENSE").open("a", encoding="utf-8", newline="\n") as handle:
                handle.write("\n" + token + "\n")
            (root / ".env.production").write_text(
                "synthetic=true\n", encoding="utf-8"
            )
            completed = validate(root)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("binary file is not explicitly declared", completed.stdout)
            self.assertIn("possible credential assignment", completed.stdout)
            self.assertIn("sensitive filename or directory name", completed.stdout)

    def test_ignored_cache_and_venv_are_not_privacy_scanned(self) -> None:
        with cloned_source() as (_base, root):
            token = "API_" + "KEY=" + ("b" * 24)
            for directory_name in ("cache", ".venv"):
                directory = root / directory_name
                directory.mkdir()
                (directory / "private.txt").write_bytes(
                    token.encode("utf-8") + b"\xff"
                )
            completed = validate(root)
            self.assertEqual(
                completed.returncode,
                0,
                completed.stderr or completed.stdout,
            )

    def test_deny_term_scans_path_names(self) -> None:
        with cloned_source() as (_base, root):
            denied = "sensitive-codename"
            directory = root / denied
            directory.mkdir()
            (directory / "safe.txt").write_text("ordinary\n", encoding="utf-8")
            completed = validate(root, "--deny-term", denied)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("path contains denied term", completed.stdout)

    def test_symbolic_link_is_rejected_when_platform_supports_it(self) -> None:
        with cloned_source() as (base, root):
            outside = base / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            link = root / "linked.txt"
            try:
                link.symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            completed = validate(root)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("symbolic links are not allowed", completed.stdout)


if __name__ == "__main__":
    unittest.main()
