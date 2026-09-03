"""Synthetic tests for the read-only workspace-memory auditor."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "manage-workspace-memory"
    / "scripts"
    / "audit_workspace_memory.py"
)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="strict")


def tree_snapshot(root: Path) -> tuple[tuple[str, str, bytes], ...]:
    snapshot: list[tuple[str, str, bytes]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        relative = path.relative_to(root).as_posix()
        if path.is_dir():
            snapshot.append((relative, "directory", b""))
        else:
            snapshot.append((relative, "file", path.read_bytes()))
    return tuple(snapshot)


def run_audit(root: Path) -> subprocess.CompletedProcess[str]:
    before = tree_snapshot(root)
    environment = os.environ.copy()
    # Simulate the legacy Windows console setup that previously produced
    # truncated mojibake.  The auditor must still emit deterministic UTF-8.
    environment["PYTHONUTF8"] = "0"
    environment["PYTHONIOENCODING"] = "cp936"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--format", "json"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=environment,
    )
    after = tree_snapshot(root)
    if before != after:
        raise AssertionError("The read-only auditor modified its audit root.")
    return completed


@contextmanager
def temporary_workspace(prefix: str) -> Iterator[Path]:
    """Create fixtures under the operating system's temporary directory."""

    with tempfile.TemporaryDirectory(prefix=prefix) as directory:
        yield Path(directory)


def valid_status(parent_link: str, evidence_link: str) -> str:
    return f"""# Current Status

- Last verified: 2026-08-20 12:00 +08:00
- Verification method: local artifact inspection
- Parent memory route: [Route]({parent_link})

## Objective

Keep the workspace resumable.

## Verified State

Local evidence is available at [task evidence]({evidence_link}).

## First Safe Next Action

Inspect the next bounded input.

## Blockers and Decisions Needed

None.
"""


class WorkspaceMemoryAuditTests(unittest.TestCase):
    def test_valid_chinese_and_space_path_returns_zero(self) -> None:
        with temporary_workspace("工作区 审计 ") as root:
            write_text(
                root / "README.md",
                "# Workspace\n\n[Memory](memory/MEMORY.md)\n\n## Current Status\n\nSee the routed status file.\n",
            )
            write_text(
                root / "memory" / "MEMORY.md",
                """# Memory

[Current status](STATUS.md)
[Asset registry](ASSET_INDEX.md)

## Shared Authorities

| Stable ID | Role |
| --- | --- |
| artifact:report:v1.2 | submitted report |

### artifact:report:v1.2
""",
            )
            write_text(
                root / "memory" / "ASSET_INDEX.md",
                """# Asset Index: Reports

| Stable ID | Asset and purpose | Authority state | Location |
| --- | --- | --- | --- |
| artifact:report:v1.2 | submitted report | authoritative | report-v1.2.pdf |
""",
            )
            write_text(
                root / "memory" / "STATUS.md",
                """# Current Status

- Last verified: 2026-08-20 10:00 +08:00
- Verification method: artifact inspection
- Parent memory route: [Memory](MEMORY.md)

## Objective

Verify the handoff.

## Verified State

The submitted artifact is [report-v1.2.pdf](report-v1.2.pdf).
SHA-256: {digest}

## Current Authorities

| Fact | Stable ID | Authority |
| --- | --- | --- |
| Report | artifact:report:v1.2 | report-v1.2.pdf |

## First Safe Next Action

Inspect the next input.

## Blockers and Decisions Needed

None.
""".format(digest="0123456789abcdef" * 4),
            )
            (root / "memory" / "report-v1.2.pdf").write_bytes(b"synthetic")

            completed = run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["issue_count"], 0)
            self.assertEqual(payload["status_files"], ["memory/STATUS.md"])
            self.assertEqual(
                payload["three_hop_routes"],
                [
                    "README.md -> memory/MEMORY.md -> memory/STATUS.md -> "
                    "memory/report-v1.2.pdf"
                ],
            )

    def test_reports_escape_broken_link_placeholder_duplicate_id_and_status(self) -> None:
        with temporary_workspace("workspace-audit-") as root:
            write_text(
                root / "README.md",
                """# Workspace

[Escape](../outside.md)
[Missing](missing.md)
[Missing angle destination](<missing file.md>)
[Template destination](<relative-link>)
[Status](STATUS.md)
[Design A](design-a.md)
[Design B](design-b.md)

- Stable ID: asset-alpha
""",
            )
            write_text(
                root / "design-a.md",
                "# Stable Design A\n\n- Design ID: asset-alpha\n",
            )
            write_text(
                root / "design-b.md",
                "# Stable Design B\n\n- Design ID: ASSET-ALPHA\n",
            )
            write_text(
                root / "STATUS.md",
                """# Current Status: <scope>

- Design ID: ASSET-ALPHA

## Objective

The report was submitted without an immutable identity record.
""",
            )

            completed = run_audit(root)

            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            codes = {issue["code"] for issue in payload["issues"]}
            self.assertTrue(
                {
                    "BROKEN_MARKDOWN_LINK",
                    "DUPLICATE_STABLE_ID",
                    "FROZEN_BASELINE_IDENTITY_MISSING",
                    "MARKDOWN_PATH_ESCAPE",
                    "STATUS_FIELDS_MISSING",
                    "UNRESOLVED_TEMPLATE_PLACEHOLDER",
                }.issubset(codes)
            )
            broken_messages = [
                issue["message"]
                for issue in payload["issues"]
                if issue["code"] == "BROKEN_MARKDOWN_LINK"
            ]
            self.assertTrue(any("missing file.md" in message for message in broken_messages))
            self.assertFalse(any("relative-link" in message for message in broken_messages))
            locations = [
                (issue["path"].casefold(), issue["path"], issue["line"] or 0, issue["code"])
                for issue in payload["issues"]
            ]
            self.assertEqual(locations, sorted(locations))

    def test_placeholder_examples_in_code_are_ignored_but_prose_is_reported(self) -> None:
        with temporary_workspace("placeholder-context-") as root:
            write_text(
                root / "README.md",
                """# Workspace

[Status](STATUS.md)

An inline tutorial token such as `<scope>` is an example.

~~~markdown
<relative-link>
{{owner}}
~~~

The unresolved owner is <owner>.
""",
            )
            write_text(root / "STATUS.md", valid_status("README.md", "evidence.txt"))
            (root / "evidence.txt").write_bytes(b"evidence")

            completed = run_audit(root)

            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            placeholder_issues = [
                issue
                for issue in payload["issues"]
                if issue["code"] == "UNRESOLVED_TEMPLATE_PLACEHOLDER"
            ]
            self.assertEqual(len(placeholder_issues), 1)
            self.assertIn("<owner>", placeholder_issues[0]["message"])

    def test_status_labels_with_empty_or_placeholder_values_do_not_pass(self) -> None:
        with temporary_workspace("status-values-") as root:
            write_text(root / "README.md", "# Workspace\n\n[Status](STATUS.md)\n")
            write_text(
                root / "STATUS.md",
                """# Current Status

- Last verified:
- Verification method: `<method>`
- Parent memory route: {{route}}

## Objective

TODO

## Verified State

<current-state>

## First Safe Next Action

TBD

## Blockers and Decisions Needed

<blocker>

## Evidence

[Local evidence](evidence.txt)
""",
            )
            (root / "evidence.txt").write_bytes(b"evidence")

            completed = run_audit(root)

            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            status_issue = next(
                issue
                for issue in payload["issues"]
                if issue["code"] == "STATUS_FIELDS_MISSING"
            )
            for field_name in (
                "objective/current stage",
                "last verified",
                "verification method",
                "parent memory route",
                "verified/current state",
                "first/next action",
                "blockers/decisions",
            ):
                self.assertIn(field_name, status_issue["message"])

    def test_custom_connected_layout_has_a_three_hop_resumption_route(self) -> None:
        with temporary_workspace("自定义 路由 ") as root:
            write_text(
                root / "README.md",
                """# Workspace

[Open the control map][control]

[control]: <控制 面/导航入口.md>
""",
            )
            write_text(
                root / "控制 面" / "导航入口.md",
                """# 任意恢复控制面

[Live panel][live]

[live]: <../状态 区/此刻.md>
""",
            )
            write_text(
                root / "状态 区" / "此刻.md",
                valid_status("<../控制 面/导航入口.md>", "../证据/依据.md"),
            )
            write_text(root / "证据" / "依据.md", "# Evidence\n\nVerified locally.\n")

            completed = run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(
                payload["three_hop_routes"],
                [
                    "README.md -> 控制 面/导航入口.md -> 状态 区/此刻.md -> "
                    "证据/依据.md"
                ],
            )

    def test_connected_but_overlong_route_does_not_pass_by_file_count(self) -> None:
        with temporary_workspace("overlong-route-") as root:
            write_text(root / "README.md", "# Workspace\n\n[One](one.md)\n")
            write_text(root / "one.md", "# One\n\n[Two](two.md)\n")
            write_text(root / "two.md", "# Two\n\n[Status](STATUS.md)\n")
            write_text(root / "STATUS.md", valid_status("two.md", "evidence.txt"))
            (root / "evidence.txt").write_bytes(b"evidence")

            completed = run_audit(root)

            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["three_hop_routes"], [])
            self.assertIn(
                "THREE_HOP_ROUTE_MISSING",
                {issue["code"] for issue in payload["issues"]},
            )

    def test_existing_inline_code_path_can_supply_local_task_evidence(self) -> None:
        with temporary_workspace("inline-path-route-") as root:
            write_text(root / "README.md", "# Workspace\n\n[Status](STATUS.md)\n")
            status = valid_status("README.md", "evidence.txt").replace(
                "[task evidence](evidence.txt)", "`evidence.txt`"
            )
            write_text(root / "STATUS.md", status)
            (root / "evidence.txt").write_bytes(b"evidence")

            completed = run_audit(root)

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(
                payload["three_hop_routes"],
                ["README.md -> STATUS.md -> evidence.txt"],
            )

    def test_invalid_utf8_is_exit_two(self) -> None:
        with temporary_workspace("workspace-audit-") as root:
            (root / "README.md").write_bytes(b"# invalid\n\xff\n")

            completed = run_audit(root)

            self.assertEqual(completed.returncode, 2)
            self.assertEqual(completed.stdout, "")
            payload = json.loads(completed.stderr)
            self.assertFalse(payload["ok"])
            self.assertIn("strict UTF-8", payload["error"])


if __name__ == "__main__":
    unittest.main()
