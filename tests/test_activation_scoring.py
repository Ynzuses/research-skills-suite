"""Tests for deterministic scoring of recorded Skill activation runs."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


TEST_ROOT = Path(__file__).resolve().parent
GOLDEN = TEST_ROOT / "golden-prompts.tsv"
SCORER = TEST_ROOT / "score_activation_results.py"
RESULT_FIELDS = [
    "case_id",
    "model",
    "run_date",
    "session_id",
    "transcript_path",
    "transcript_sha256",
    "loaded_skills",
    "behavior_pass",
    "notes",
]


@contextmanager
def result_path() -> Iterator[Path]:
    root = TEST_ROOT / f".activation-{uuid.uuid4().hex}"
    root.mkdir(parents=False, exist_ok=False)
    try:
        yield root / "results.tsv"
    finally:
        shutil.rmtree(root)


def expected_rows() -> list[dict[str, str]]:
    with GOLDEN.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_release_trees(root: Path) -> tuple[Path, Path, str]:
    candidate = root / "candidate"
    manifest_dir = candidate / ".codex-plugin"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "plugin.json").write_text(
        json.dumps(
            {
                "name": "research-skills-suite",
                "version": "0.6.0",
                "description": "Synthetic activation-scoring fixture",
                "skills": "./skills/",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (candidate / "README.md").write_text(
        "# Synthetic release fixture\n", encoding="utf-8"
    )
    entries: list[tuple[str, str]] = []
    for path in sorted(
        (item for item in candidate.rglob("*") if item.is_file()),
        key=lambda item: item.relative_to(candidate).as_posix(),
    ):
        entries.append((file_sha256(path), path.relative_to(candidate).as_posix()))
    sha_file = candidate / "SHA256SUMS"
    sha_file.write_text(
        "".join(f"{digest}  {relative}\n" for digest, relative in entries),
        encoding="utf-8",
    )
    installed = root / "installed"
    shutil.copytree(candidate, installed)
    return candidate, installed, file_sha256(sha_file)


def write_results(
    path: Path,
    *,
    mutate: object | None = None,
    limit: int | None = None,
) -> None:
    candidate, installed, candidate_digest = create_release_trees(path.parent)
    evidence_root = path.parent / "evidence"
    transcript_root = evidence_root / "transcripts"
    transcript_root.mkdir(parents=True)
    rows = expected_rows()
    if limit is not None:
        rows = rows[:limit]
    sessions: list[dict[str, object]] = []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS, delimiter="\t")
        writer.writeheader()
        for index, row in enumerate(rows):
            session_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"activation:{row['id']}"))
            transcript = transcript_root / f"{row['id']}.txt"
            transcript.write_text(
                f"synthetic session evidence for {row['id']}\n",
                encoding="utf-8",
            )
            transcript_relative = transcript.relative_to(evidence_root).as_posix()
            transcript_digest = file_sha256(transcript)
            result = {
                "case_id": row["id"],
                "model": "synthetic-runner",
                "run_date": "2026-08-20",
                "session_id": session_id,
                "transcript_path": transcript_relative,
                "transcript_sha256": transcript_digest,
                "loaded_skills": row["expected_skills"],
                "behavior_pass": "true",
                "notes": "synthetic scoring fixture",
            }
            if callable(mutate):
                mutate(index, row, result)
            writer.writerow(result)
            sessions.append(
                {
                    "case_id": row["id"],
                    "session_id": result["session_id"],
                    "fresh_session": True,
                    "prompt_sha256": hashlib.sha256(
                        row["prompt"].encode("utf-8")
                    ).hexdigest(),
                    "transcript_path": result["transcript_path"],
                    "transcript_sha256": result["transcript_sha256"],
                }
            )
    evidence_manifest = {
        "schema_version": "1.0",
        "batch_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "activation-batch")),
        "attested_at": "2026-08-20T00:00:00+00:00",
        "operator_id": "synthetic-operator",
        "reviewer_id": "synthetic-independent-reviewer",
        "model": "synthetic-runner",
        "run_date": "2026-08-20",
        "golden_sha256": file_sha256(GOLDEN),
        "results_sha256": file_sha256(path),
        "candidate": {
            "plugin_name": "research-skills-suite",
            "version": "0.6.0",
            "sha256s_sha256": candidate_digest,
        },
        "installation": {
            "receipt_id": str(uuid.uuid5(uuid.NAMESPACE_URL, "activation-install")),
            "installed_at": "2026-08-20T00:00:00+00:00",
            "fresh_install": True,
            "host_product": "Codex",
            "host_version": "synthetic",
            "install_method": "synthetic clean copy",
            "candidate_sha256s_sha256": candidate_digest,
            "installed_sha256s_sha256": file_sha256(installed / "SHA256SUMS"),
        },
        "sessions": sessions,
    }
    (evidence_root / "activation-evidence.json").write_text(
        json.dumps(evidence_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def score(
    path: Path, *extra: str
) -> subprocess.CompletedProcess[str]:
    command = [
            sys.executable,
            str(SCORER),
            "--results",
            str(path),
            "--candidate-root",
            str(path.parent / "candidate"),
            "--installed-root",
            str(path.parent / "installed"),
            "--evidence-manifest",
            str(path.parent / "evidence" / "activation-evidence.json"),
            "--format",
            "json",
            "--min-precision",
            "1",
            "--min-recall",
            "1",
            "--min-exact-routing",
            "1",
        ]
    command.extend(extra)
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )


class ActivationScoringTests(unittest.TestCase):
    def test_perfect_recorded_run_passes(self) -> None:
        with result_path() as path:
            write_results(path)
            completed = score(path)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["pass"])
            self.assertFalse(payload["partial"])
            self.assertEqual(payload["forbidden_activation_count"], 0)
            self.assertEqual(set(payload["per_class"]), {
                "direct",
                "indirect",
                "incomplete",
                "boundary",
                "composition",
                "negative",
            })
            for metrics in payload["per_skill"].values():
                self.assertEqual(metrics["precision"], 1.0)
                self.assertEqual(metrics["recall"], 1.0)
                self.assertTrue(metrics["pass"])

    def test_missing_expected_activation_fails(self) -> None:
        with result_path() as path:
            def mutate(index: int, _golden: dict[str, str], result: dict[str, str]) -> None:
                if index == 0:
                    result["loaded_skills"] = "none"

            write_results(path, mutate=mutate)
            completed = score(path)
            self.assertEqual(completed.returncode, 1)
            self.assertIn('"pass": false', completed.stdout)

    def test_forbidden_activation_is_an_absolute_gate(self) -> None:
        rows = expected_rows()
        boundary_index = next(
            index
            for index, row in enumerate(rows)
            if row["forbidden_skills"] != "none"
        )

        def mutate(index: int, golden: dict[str, str], result: dict[str, str]) -> None:
            if index == boundary_index:
                result["loaded_skills"] = golden["forbidden_skills"].split("+", 1)[0]

        with result_path() as path:
            write_results(path, mutate=mutate)
            completed = score(
                path,
                "--min-precision",
                "0",
                "--min-recall",
                "0",
                "--min-exact-routing",
                "0",
                "--min-skill-precision",
                "0",
                "--min-skill-recall",
                "0",
                "--min-class-exact-routing",
                "0",
            )
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertGreater(payload["forbidden_activation_count"], 0)
            self.assertFalse(payload["pass"])

    def test_each_class_has_an_exact_routing_gate(self) -> None:
        target_class = "indirect"
        rows = expected_rows()
        target_index = next(
            index for index, row in enumerate(rows) if row["class"] == target_class
        )

        def mutate(index: int, _golden: dict[str, str], result: dict[str, str]) -> None:
            if index == target_index:
                result["loaded_skills"] = "none"

        with result_path() as path:
            write_results(path, mutate=mutate)
            completed = score(
                path,
                "--min-precision",
                "0",
                "--min-recall",
                "0",
                "--min-exact-routing",
                "0",
                "--min-skill-precision",
                "0",
                "--min-skill-recall",
                "0",
                "--min-class-exact-routing",
                "1",
            )
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["per_class"][target_class]["pass"])

    def test_zero_recall_skill_fails_even_with_zero_thresholds(self) -> None:
        target_skill = expected_rows()[0]["target_skill"]

        def mutate(_index: int, golden: dict[str, str], result: dict[str, str]) -> None:
            loaded = {
                skill
                for skill in golden["expected_skills"].split("+")
                if skill and skill != "none" and skill != target_skill
            }
            result["loaded_skills"] = "+".join(sorted(loaded)) or "none"

        with result_path() as path:
            write_results(path, mutate=mutate)
            completed = score(
                path,
                "--min-precision",
                "0",
                "--min-recall",
                "0",
                "--min-exact-routing",
                "0",
                "--min-skill-precision",
                "0",
                "--min-skill-recall",
                "0",
                "--min-class-exact-routing",
                "0",
            )
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertIn(target_skill, payload["zero_recall_skills"])

    def test_partial_run_is_diagnostic_only(self) -> None:
        with result_path() as path:
            write_results(path, limit=1)
            completed = score(
                path,
                "--allow-partial",
                "--min-precision",
                "0",
                "--min-recall",
                "0",
                "--min-exact-routing",
                "0",
                "--min-skill-precision",
                "0",
                "--min-skill-recall",
                "0",
                "--min-class-exact-routing",
                "0",
            )
            self.assertEqual(completed.returncode, 1)
            payload = json.loads(completed.stdout)
            self.assertTrue(payload["partial"])
            self.assertFalse(payload["release_eligible"])
            self.assertFalse(payload["pass"])

    def test_mixed_model_or_run_date_is_rejected(self) -> None:
        for field, value in (
            ("model", "different-model"),
            ("run_date", "2026-08-21"),
        ):
            with self.subTest(field=field), result_path() as path:
                def mutate(
                    index: int,
                    _golden: dict[str, str],
                    result: dict[str, str],
                    *,
                    field: str = field,
                    value: str = value,
                ) -> None:
                    if index == 1:
                        result[field] = value

                write_results(path, mutate=mutate)
                completed = score(path)
                self.assertEqual(completed.returncode, 2)
                self.assertIn("all rows must use one", completed.stderr)

    def test_non_iso_run_date_is_rejected_without_traceback(self) -> None:
        def mutate(
            _index: int,
            _golden: dict[str, str],
            result: dict[str, str],
        ) -> None:
            result["run_date"] = "20-08-2026"

        with result_path() as path:
            write_results(path, mutate=mutate)
            completed = score(path)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("ISO calendar date", completed.stderr)
            self.assertNotIn("Traceback", completed.stderr)

    def test_candidate_mutation_breaks_hash_binding(self) -> None:
        with result_path() as path:
            write_results(path)
            (path.parent / "candidate" / "README.md").write_text(
                "mutated after evidence capture\n", encoding="utf-8"
            )
            completed = score(path)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("hash mismatch", completed.stderr)

    def test_installed_tree_must_match_candidate(self) -> None:
        with result_path() as path:
            write_results(path)
            (path.parent / "installed" / "unexpected.txt").write_text(
                "unexpected\n", encoding="utf-8"
            )
            completed = score(path)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("does not match SHA256SUMS", completed.stderr)

    def test_transcript_hash_is_required(self) -> None:
        with result_path() as path:
            write_results(path)
            transcript = next((path.parent / "evidence" / "transcripts").iterdir())
            transcript.write_text("changed transcript\n", encoding="utf-8")
            completed = score(path)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("transcript_sha256 mismatch", completed.stderr)

    def test_results_are_bound_to_external_manifest(self) -> None:
        with result_path() as path:
            write_results(path)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("\n")
            completed = score(path)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("results_sha256", completed.stderr)

    def test_operator_cannot_self_attest_as_reviewer(self) -> None:
        with result_path() as path:
            write_results(path)
            manifest_path = path.parent / "evidence" / "activation-evidence.json"
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            payload["reviewer_id"] = payload["operator_id"]
            manifest_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            completed = score(path)
            self.assertEqual(completed.returncode, 2)
            self.assertIn("must differ", completed.stderr)


if __name__ == "__main__":
    unittest.main()
