"""Synthetic regression tests for the read-only review-bundle validator."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import uuid
from contextlib import contextmanager
from typing import Iterator


SKILL = Path(__file__).resolve().parents[1] / "evidence-traceable-literature-review"
SCRIPT = SKILL / "scripts" / "validate_review_bundle.py"
ASSETS = SKILL / "assets"
TABLES = (
    "search-ledger.tsv",
    "screening-ledger.tsv",
    "evidence-matrix.tsv",
    "source-manifest.tsv",
)


@contextmanager
def temporary_test_root() -> Iterator[Path]:
    """Create a unique fixture under the writable current workspace."""

    root = Path.cwd() / f".review-bundle-test-{uuid.uuid4().hex}"
    root.mkdir(parents=False, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root)


def append_row(path: Path, values: list[str]) -> None:
    with path.open("a", encoding="utf-8", errors="strict", newline="") as handle:
        handle.write("\t".join(values) + "\n")


def copy_templates(bundle: Path) -> None:
    bundle.mkdir(parents=True)
    for filename in TABLES:
        shutil.copy2(ASSETS / filename, bundle / filename)


def create_valid_bundle(bundle: Path, *, orphan: bool = False) -> str:
    copy_templates(bundle)
    package = bundle / "full-text"
    package.mkdir()
    full_text = package / "paper.txt"
    full_text.write_text("Synthetic full text for structural testing.\n", encoding="utf-8")
    if orphan:
        (package / "orphan.txt").write_text("Synthetic orphan.\n", encoding="utf-8")
    digest = hashlib.sha256(full_text.read_bytes()).hexdigest()

    append_row(
        bundle / "search-ledger.tsv",
        [
            "search-1",
            "Synthetic database",
            "2026-01-02",
            "synthetic query",
            "",
            "page=1",
            "2",
            "1",
            "",
            "complete",
            "synthetic fixture",
        ],
    )
    append_row(
        bundle / "source-manifest.tsv",
        [
            "source-1",
            "Synthetic citation",
            "synthetic:1",
            "version-1",
            "original_study",
            "present",
            "full-text/paper.txt",
            digest,
            "synthetic fixture",
        ],
    )
    append_row(
        bundle / "screening-ledger.tsv",
        [
            "record-1",
            "search-1",
            "source-1",
            "Synthetic source",
            "2026",
            "full_text",
            "include",
            "1",
            "true",
            "",
            "meets synthetic criteria",
            "original_study",
            "synthetic fixture",
        ],
    )
    append_row(
        bundle / "evidence-matrix.tsv",
        [
            "evidence-1",
            "claim-1",
            "Synthetic claim",
            "fact",
            "source-1",
            "original_study",
            "section 1",
            "Synthetic excerpt.",
            "synthetic scope",
            "supports",
            "direct",
            "result",
            "synthetic fixture",
        ],
    )
    return digest


def run_validator(
    bundle: Path,
    report_format: str = "json",
    *,
    strict_release: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "--bundle",
        str(bundle),
        "--format",
        report_format,
    ]
    if strict_release:
        command.append("--strict-release")
    environment = os.environ.copy()
    environment.pop("PYTHONUTF8", None)
    environment.pop("PYTHONIOENCODING", None)
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        env=environment,
    )


def snapshot_files(root: Path) -> dict[str, tuple[int, int, str]]:
    snapshot: dict[str, tuple[int, int, str]] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        stat = path.stat()
        snapshot[path.relative_to(root).as_posix()] = (
            stat.st_size,
            stat.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest(),
        )
    return snapshot


class ReviewBundleValidatorTests(unittest.TestCase):
    def test_header_only_templates_are_valid(self) -> None:
        with temporary_test_root() as temporary:
            bundle = temporary / "bundle"
            copy_templates(bundle)
            result = run_validator(bundle)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(report["error_count"], 0)
            self.assertEqual(report["warning_count"], 0)

    def test_valid_bundle_and_orphan_warning_return_zero(self) -> None:
        with temporary_test_root() as temporary:
            bundle = temporary / "bundle"
            create_valid_bundle(bundle, orphan=True)
            first = run_validator(bundle)
            second = run_validator(bundle)
            report = json.loads(first.stdout)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(report["error_count"], 0)
            self.assertEqual(report["warning_count"], 1)
            self.assertEqual(report["issues"][0]["code"], "orphan_package_member")

            strict = run_validator(bundle, strict_release=True)
            strict_report = json.loads(strict.stdout)
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertEqual(strict_report["warning_count"], 0)
            self.assertEqual(strict_report["error_count"], 1)
            self.assertEqual(strict_report["issues"][0]["code"], "orphan_package_member")
            self.assertEqual(strict_report["issues"][0]["severity"], "error")

    def test_historical_decisions_are_closed_and_only_current_decision_includes(self) -> None:
        with temporary_test_root() as temporary:
            included_bundle = temporary / "included-history"
            create_valid_bundle(included_bundle)
            screening = included_bundle / "screening-ledger.tsv"
            header = screening.read_text(encoding="utf-8").splitlines()[0] + "\n"
            screening.write_text(header, encoding="utf-8")
            append_row(
                screening,
                [
                    "record-old",
                    "search-1",
                    "source-1",
                    "Synthetic source",
                    "2026",
                    "abstract",
                    "exclude",
                    "1",
                    "false",
                    "",
                    "insufficient detail before full-text review",
                    "original_study",
                    "historical fixture",
                ],
            )
            append_row(
                screening,
                [
                    "record-current",
                    "search-1",
                    "source-1",
                    "Synthetic source",
                    "2026",
                    "full_text",
                    "include",
                    "2",
                    "true",
                    "record-old",
                    "meets criteria after full-text review",
                    "original_study",
                    "current fixture",
                ],
            )
            included = run_validator(included_bundle)
            self.assertEqual(included.returncode, 0, included.stdout + included.stderr)

            excluded_bundle = temporary / "excluded-history"
            create_valid_bundle(excluded_bundle)
            screening = excluded_bundle / "screening-ledger.tsv"
            header = screening.read_text(encoding="utf-8").splitlines()[0] + "\n"
            screening.write_text(header, encoding="utf-8")
            append_row(
                screening,
                [
                    "record-old",
                    "search-1",
                    "source-1",
                    "Synthetic source",
                    "2026",
                    "abstract",
                    "include",
                    "1",
                    "false",
                    "",
                    "initial decision",
                    "original_study",
                    "historical fixture",
                ],
            )
            append_row(
                screening,
                [
                    "record-current",
                    "search-1",
                    "source-1",
                    "Synthetic source",
                    "2026",
                    "full_text",
                    "exclude",
                    "2",
                    "true",
                    "record-old",
                    "fails full-text eligibility criteria",
                    "original_study",
                    "current fixture",
                ],
            )
            excluded = run_validator(excluded_bundle)
            excluded_codes = {
                issue["code"] for issue in json.loads(excluded.stdout)["issues"]
            }
            self.assertEqual(excluded.returncode, 1, excluded.stdout + excluded.stderr)
            self.assertIn("source_not_included", excluded_codes)

    def test_ambiguous_and_unresolved_decision_histories_fail_closed(self) -> None:
        with temporary_test_root() as temporary:
            ambiguous_bundle = temporary / "ambiguous-history"
            create_valid_bundle(ambiguous_bundle)
            append_row(
                ambiguous_bundle / "screening-ledger.tsv",
                [
                    "record-2",
                    "search-1",
                    "source-1",
                    "Synthetic source",
                    "2026",
                    "full_text",
                    "exclude",
                    "2",
                    "true",
                    "",
                    "conflicting current decision",
                    "original_study",
                    "ambiguous fixture",
                ],
            )
            ambiguous = run_validator(ambiguous_bundle)
            ambiguous_codes = {
                issue["code"] for issue in json.loads(ambiguous.stdout)["issues"]
            }
            self.assertEqual(ambiguous.returncode, 1, ambiguous.stdout + ambiguous.stderr)
            self.assertIn("ambiguous_current_decision", ambiguous_codes)

            unresolved_bundle = temporary / "unresolved-history"
            create_valid_bundle(unresolved_bundle)
            screening = unresolved_bundle / "screening-ledger.tsv"
            content = screening.read_text(encoding="utf-8")
            screening.write_text(
                content.replace(
                    "\ttrue\t\tmeets synthetic criteria",
                    "\ttrue\tmissing-record\tmeets synthetic criteria",
                ),
                encoding="utf-8",
            )
            unresolved = run_validator(unresolved_bundle)
            unresolved_codes = {
                issue["code"] for issue in json.loads(unresolved.stdout)["issues"]
            }
            self.assertEqual(unresolved.returncode, 1, unresolved.stdout + unresolved.stderr)
            self.assertIn("unresolved_supersedes_record_id", unresolved_codes)

            unclosed_bundle = temporary / "unclosed-history"
            create_valid_bundle(unclosed_bundle)
            screening = unclosed_bundle / "screening-ledger.tsv"
            original = screening.read_text(encoding="utf-8")
            screening.write_text(
                original.replace("\ttrue\t\t", "\tfalse\t\t"),
                encoding="utf-8",
            )
            append_row(
                screening,
                [
                    "record-current",
                    "search-1",
                    "source-1",
                    "Synthetic source",
                    "2026",
                    "full_text",
                    "include",
                    "2",
                    "true",
                    "",
                    "new decision omitted its history link",
                    "original_study",
                    "unclosed fixture",
                ],
            )
            unclosed = run_validator(unclosed_bundle)
            unclosed_codes = {
                issue["code"] for issue in json.loads(unclosed.stdout)["issues"]
            }
            self.assertEqual(unclosed.returncode, 1, unclosed.stdout + unclosed.stderr)
            self.assertIn("unclosed_decision_history", unclosed_codes)

    def test_complete_search_count_contract_handles_blank_values_explicitly(self) -> None:
        with temporary_test_root() as temporary:
            excessive_bundle = temporary / "excessive-saved-count"
            create_valid_bundle(excessive_bundle)
            ledger = excessive_bundle / "search-ledger.tsv"
            ledger.write_text(
                ledger.read_text(encoding="utf-8").replace("\t2\t1\t", "\t2\t3\t"),
                encoding="utf-8",
            )
            excessive = run_validator(excessive_bundle)
            excessive_codes = {
                issue["code"] for issue in json.loads(excessive.stdout)["issues"]
            }
            self.assertEqual(excessive.returncode, 1, excessive.stdout + excessive.stderr)
            self.assertIn("saved_count_exceeds_raw_count", excessive_codes)

            blank_bundle = temporary / "blank-counts"
            create_valid_bundle(blank_bundle)
            ledger = blank_bundle / "search-ledger.tsv"
            ledger.write_text(
                ledger.read_text(encoding="utf-8").replace("\t2\t1\t", "\t\t\t"),
                encoding="utf-8",
            )
            blank = run_validator(blank_bundle)
            blank_report = json.loads(blank.stdout)
            self.assertEqual(blank.returncode, 0, blank.stdout + blank.stderr)
            self.assertEqual(
                [issue["code"] for issue in blank_report["issues"]],
                ["complete_search_counts_missing"],
            )
            blank_strict = run_validator(blank_bundle, strict_release=True)
            self.assertEqual(
                blank_strict.returncode,
                1,
                blank_strict.stdout + blank_strict.stderr,
            )

            incomplete_bundle = temporary / "incomplete-count-pair"
            create_valid_bundle(incomplete_bundle)
            ledger = incomplete_bundle / "search-ledger.tsv"
            ledger.write_text(
                ledger.read_text(encoding="utf-8").replace("\t2\t1\t", "\t2\t\t"),
                encoding="utf-8",
            )
            incomplete = run_validator(incomplete_bundle)
            incomplete_codes = {
                issue["code"] for issue in json.loads(incomplete.stdout)["issues"]
            }
            self.assertEqual(incomplete.returncode, 1, incomplete.stdout + incomplete.stderr)
            self.assertIn("incomplete_count_pair", incomplete_codes)

            partial_bundle = temporary / "partial-count"
            create_valid_bundle(partial_bundle)
            ledger = partial_bundle / "search-ledger.tsv"
            ledger.write_text(
                ledger.read_text(encoding="utf-8")
                .replace("\t2\t1\t", "\t\t1\t")
                .replace("\tcomplete\t", "\tpartial\t"),
                encoding="utf-8",
            )
            partial = run_validator(partial_bundle)
            self.assertEqual(partial.returncode, 0, partial.stdout + partial.stderr)

    def test_release_strict_requires_hash_for_present_full_text(self) -> None:
        with temporary_test_root() as temporary:
            bundle = temporary / "missing-hash"
            digest = create_valid_bundle(bundle)
            manifest = bundle / "source-manifest.tsv"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(digest, ""),
                encoding="utf-8",
            )
            ordinary = run_validator(bundle)
            strict = run_validator(bundle, strict_release=True)
            strict_codes = {issue["code"] for issue in json.loads(strict.stdout)["issues"]}
            self.assertEqual(ordinary.returncode, 0, ordinary.stdout + ordinary.stderr)
            self.assertEqual(strict.returncode, 1, strict.stdout + strict.stderr)
            self.assertIn("missing_sha256", strict_codes)

    def test_unicode_space_path_is_utf8_and_validation_is_read_only(self) -> None:
        with temporary_test_root() as temporary:
            bundle = temporary / "中文 空格 review bundle"
            create_valid_bundle(bundle)
            old_path = bundle / "full-text" / "paper.txt"
            new_path = bundle / "full-text" / "论文 原文.txt"
            old_path.rename(new_path)
            manifest = bundle / "source-manifest.tsv"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    "full-text/paper.txt", "full-text/论文 原文.txt"
                ),
                encoding="utf-8",
            )
            before = snapshot_files(bundle)
            result = run_validator(bundle, strict_release=True)
            after = snapshot_files(bundle)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(report["bundle"], str(bundle.resolve()))
            self.assertEqual(before, after)

    def test_legacy_screening_header_has_stable_schema_error(self) -> None:
        with temporary_test_root() as temporary:
            bundle = temporary / "legacy-header"
            copy_templates(bundle)
            (bundle / "screening-ledger.tsv").write_text(
                "record_id\tsearch_id\tsource_id\ttitle\tyear\tstage\tdecision\t"
                "reason\tevidence_role\tnotes\n",
                encoding="utf-8",
            )
            result = run_validator(bundle)
            report = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(
                [issue["code"] for issue in report["issues"]],
                ["header_mismatch"],
            )

    def test_duplicate_and_dangling_relationships_return_one(self) -> None:
        with temporary_test_root() as temporary:
            bundle = temporary / "bundle"
            create_valid_bundle(bundle)
            append_row(
                bundle / "search-ledger.tsv",
                [
                    "search-1",
                    "Another synthetic database",
                    "2026-01-03",
                    "duplicate identifier",
                    "",
                    "page=1",
                    "1",
                    "1",
                    "",
                    "complete",
                    "synthetic duplicate",
                ],
            )
            append_row(
                bundle / "evidence-matrix.tsv",
                [
                    "evidence-2",
                    "claim-2",
                    "Synthetic dangling claim",
                    "fact",
                    "missing-source",
                    "original_study",
                    "page 1",
                    "Synthetic excerpt.",
                    "synthetic scope",
                    "supports",
                    "direct",
                    "result",
                    "synthetic dangling relationship",
                ],
            )
            result = run_validator(bundle)
            codes = {issue["code"] for issue in json.loads(result.stdout)["issues"]}
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("duplicate_id", codes)
            self.assertIn("unresolved_source_id", codes)
            self.assertIn("source_not_included", codes)

    def test_parent_path_escape_returns_one(self) -> None:
        with temporary_test_root() as temporary:
            bundle = temporary / "bundle"
            create_valid_bundle(bundle)
            append_row(
                bundle / "source-manifest.tsv",
                [
                    "source-2",
                    "Synthetic escaped citation",
                    "synthetic:2",
                    "version-1",
                    "review",
                    "present",
                    "../outside.pdf",
                    "",
                    "synthetic escape",
                ],
            )
            result = run_validator(bundle)
            codes = {issue["code"] for issue in json.loads(result.stdout)["issues"]}
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("full_text_path_escape", codes)

    def test_hash_mismatch_and_missing_file_return_one(self) -> None:
        with temporary_test_root() as temporary:
            bundle = temporary / "hash-bundle"
            digest = create_valid_bundle(bundle)
            manifest = bundle / "source-manifest.tsv"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(digest, "0" * 64),
                encoding="utf-8",
            )
            mismatch = run_validator(bundle)
            mismatch_codes = {
                issue["code"] for issue in json.loads(mismatch.stdout)["issues"]
            }
            self.assertEqual(mismatch.returncode, 1, mismatch.stdout + mismatch.stderr)
            self.assertIn("sha256_mismatch", mismatch_codes)

            missing_bundle = temporary / "missing-full-text-bundle"
            create_valid_bundle(missing_bundle)
            (missing_bundle / "full-text" / "paper.txt").unlink()
            missing = run_validator(missing_bundle)
            missing_codes = {issue["code"] for issue in json.loads(missing.stdout)["issues"]}
            self.assertEqual(missing.returncode, 1, missing.stdout + missing.stderr)
            self.assertIn("missing_full_text", missing_codes)

    def test_invalid_utf8_and_missing_table_return_two(self) -> None:
        with temporary_test_root() as temporary:
            invalid_bundle = temporary / "invalid-utf8-bundle"
            create_valid_bundle(invalid_bundle)
            (invalid_bundle / "search-ledger.tsv").write_bytes(b"\xff\xfe")
            invalid = run_validator(invalid_bundle)
            invalid_codes = {issue["code"] for issue in json.loads(invalid.stdout)["issues"]}
            self.assertEqual(invalid.returncode, 2, invalid.stdout + invalid.stderr)
            self.assertIn("invalid_utf8", invalid_codes)

            missing_bundle = temporary / "missing-table-bundle"
            create_valid_bundle(missing_bundle)
            (missing_bundle / "screening-ledger.tsv").unlink()
            missing = run_validator(missing_bundle)
            missing_codes = {issue["code"] for issue in json.loads(missing.stdout)["issues"]}
            self.assertEqual(missing.returncode, 2, missing.stdout + missing.stderr)
            self.assertIn("missing_file", missing_codes)


if __name__ == "__main__":
    unittest.main()
