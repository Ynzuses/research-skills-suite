#!/usr/bin/env python3
"""Score clean-session Skill activation evidence against golden prompts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import stat
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


GOLDEN_COLUMNS = [
    "id",
    "target_skill",
    "expected_skills",
    "forbidden_skills",
    "class",
    "prompt",
    "expected_behavior",
]
RESULT_COLUMNS = [
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
ALLOWED_CLASSES = {
    "direct",
    "indirect",
    "incomplete",
    "boundary",
    "composition",
    "negative",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SHA256SUM_RE = re.compile(r"^([0-9a-f]{64})  ([^\r\n]+)$")
EVIDENCE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    case_class: str
    expected: list[str]
    forbidden: list[str]
    loaded: list[str]
    missing: list[str]
    unexpected: list[str]
    forbidden_activated: list[str]
    behavior_pass: bool | None
    routing_pass: bool
    overall_pass: bool


def configure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (AttributeError, OSError):
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare recorded clean-session activations with the suite golden "
            "prompt specification."
        )
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=Path(__file__).with_name("golden-prompts.tsv"),
    )
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument(
        "--candidate-root",
        type=Path,
        required=True,
        help="Exported Plugin tree whose SHA256SUMS binds this run.",
    )
    parser.add_argument(
        "--installed-root",
        type=Path,
        required=True,
        help="Clean installed Plugin tree; must exactly match the candidate.",
    )
    parser.add_argument(
        "--evidence-manifest",
        type=Path,
        required=True,
        help="External activation evidence manifest with session transcript hashes.",
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--min-precision", type=float, default=0.95)
    parser.add_argument("--min-recall", type=float, default=0.90)
    parser.add_argument("--min-exact-routing", type=float, default=0.90)
    parser.add_argument(
        "--min-skill-precision",
        type=float,
        help="Per-Skill minimum; defaults to --min-precision.",
    )
    parser.add_argument(
        "--min-skill-recall",
        type=float,
        help="Per-Skill minimum; defaults to --min-recall.",
    )
    parser.add_argument(
        "--min-class-exact-routing",
        type=float,
        help="Per-class minimum; defaults to --min-exact-routing.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help=(
            "Score a subset for diagnosis. Partial evidence can never produce "
            "a release pass."
        ),
    )
    return parser.parse_args()


def parse_skill_set(value: str) -> set[str]:
    value = value.strip()
    if value == "none":
        return set()
    return {item.strip() for item in value.split("+") if item.strip()}


def read_tsv(path: Path, columns: list[str]) -> list[dict[str, str]]:
    with path.open(
        "r", encoding="utf-8", errors="strict", newline=""
    ) as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != columns:
            raise ValueError(
                f"{path}: expected columns {columns}, found {reader.fieldnames}"
            )
        return [dict(row) for row in reader]


def ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def strict_iso_date(value: str) -> bool:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed.isoformat() == value


def strict_iso_datetime(value: str) -> bool:
    if not value or value.endswith("Z"):
        value = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def has_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def require_plain_file(path: Path, label: str, *, nonempty: bool = False) -> Path:
    try:
        stat_result = path.lstat()
    except OSError as exc:
        raise ValueError(f"{label} is not readable: {path}: {exc}") from exc
    if path.is_symlink() or has_reparse_point(path) or not path.is_file():
        raise ValueError(f"{label} must be a regular non-link file: {path}")
    if getattr(stat_result, "st_nlink", 1) != 1:
        raise ValueError(f"{label} must not be a hard link: {path}")
    if nonempty and stat_result.st_size <= 0:
        raise ValueError(f"{label} must be non-empty: {path}")
    return path


def safe_relative_file(root: Path, value: str, label: str) -> Path:
    if not value or "\\" in value:
        raise ValueError(f"{label} must be a non-empty POSIX relative path")
    relative = Path(*value.split("/"))
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ValueError(f"{label} escapes its evidence root: {value!r}")
    candidate = root.joinpath(relative)
    resolved_parent = candidate.parent.resolve(strict=True)
    root_resolved = root.resolve(strict=True)
    if not is_relative_to(resolved_parent, root_resolved):
        raise ValueError(f"{label} escapes its evidence root: {value!r}")
    return require_plain_file(candidate, label, nonempty=True)


def parse_sha256s(root: Path) -> tuple[dict[str, str], str]:
    sha_file = require_plain_file(root / "SHA256SUMS", "candidate SHA256SUMS", nonempty=True)
    raw = sha_file.read_bytes()
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeError as exc:
        raise ValueError(f"SHA256SUMS is not strict UTF-8: {exc}") from exc
    entries: dict[str, str] = {}
    casefolded: dict[str, str] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        match = SHA256SUM_RE.fullmatch(line)
        if match is None:
            raise ValueError(f"SHA256SUMS:{number}: invalid line")
        digest, relative = match.groups()
        if "\\" in relative:
            raise ValueError(f"SHA256SUMS:{number}: path must use POSIX separators")
        relative_path = Path(*relative.split("/"))
        if relative_path.is_absolute() or any(
            part in {"", ".", ".."} for part in relative_path.parts
        ):
            raise ValueError(f"SHA256SUMS:{number}: unsafe path {relative!r}")
        folded = relative.casefold()
        if relative in entries or folded in casefolded:
            raise ValueError(f"SHA256SUMS:{number}: duplicate path {relative!r}")
        entries[relative] = digest
        casefolded[folded] = relative
    if not entries:
        raise ValueError("SHA256SUMS has no entries")
    return entries, sha256_bytes(raw)


def regular_tree_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    folded: dict[str, str] = {}
    for parent, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        parent_path = Path(parent)
        for name in list(dirnames):
            directory = parent_path / name
            if directory.is_symlink() or has_reparse_point(directory):
                raise ValueError(f"tree contains linked directory: {directory}")
        for name in filenames:
            path = parent_path / name
            require_plain_file(path, "tree member")
            relative = path.relative_to(root).as_posix()
            key = relative.casefold()
            if key in folded:
                raise ValueError(
                    f"tree has case-colliding paths: {folded[key]!r}, {relative!r}"
                )
            folded[key] = relative
            files[relative] = path
    return files


def verify_release_tree(root: Path) -> tuple[dict[str, str], str, dict[str, Any]]:
    original = root.expanduser()
    try:
        original.lstat()
    except OSError as exc:
        raise ValueError(f"release tree is not readable: {original}: {exc}") from exc
    if original.is_symlink() or has_reparse_point(original) or not original.is_dir():
        raise ValueError(f"release tree must be a regular non-link directory: {original}")
    root = original.resolve(strict=True)
    entries, sha_file_digest = parse_sha256s(root)
    files = regular_tree_files(root)
    actual = set(files) - {"SHA256SUMS"}
    expected = set(entries)
    if actual != expected:
        missing = sorted(expected - actual)[:5]
        extra = sorted(actual - expected)[:5]
        raise ValueError(
            f"release tree does not match SHA256SUMS; missing={missing}, extra={extra}"
        )
    for relative, expected_digest in entries.items():
        actual_digest = sha256_file(files[relative])
        if actual_digest != expected_digest:
            raise ValueError(f"release tree hash mismatch: {relative}")
    manifest_path = require_plain_file(
        root / ".codex-plugin" / "plugin.json", "Plugin manifest", nonempty=True
    )
    try:
        plugin = json.loads(manifest_path.read_text(encoding="utf-8", errors="strict"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Plugin manifest: {exc}") from exc
    if not isinstance(plugin, dict):
        raise ValueError("Plugin manifest must be a JSON object")
    return entries, sha_file_digest, plugin


def valid_uuid(value: str) -> bool:
    try:
        return str(uuid.UUID(value)) == value.lower()
    except (ValueError, AttributeError):
        return False


def required_text(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def required_bool(mapping: dict[str, Any], key: str, context: str) -> bool:
    value = mapping.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{context}.{key} must be boolean")
    return value


def required_sha256(mapping: dict[str, Any], key: str, context: str) -> str:
    value = required_text(mapping, key, context).lower()
    if SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{context}.{key} must be a lower-case SHA-256 digest")
    return value


def verify_evidence_manifest(
    *,
    manifest_path: Path,
    golden_path: Path,
    results_path: Path,
    candidate_root: Path,
    installed_root: Path,
    candidate_sha256s: str,
    installed_sha256s: str,
    plugin: dict[str, Any],
    golden: dict[str, dict[str, Any]],
    observed: dict[str, dict[str, str]],
    models: set[str],
    run_dates: set[str],
) -> dict[str, Any]:
    manifest_path = require_plain_file(
        manifest_path.expanduser(), "activation evidence manifest", nonempty=True
    ).resolve(strict=True)
    candidate_root = candidate_root.resolve(strict=True)
    installed_root = installed_root.resolve(strict=True)
    if is_relative_to(manifest_path, candidate_root) or is_relative_to(
        manifest_path, installed_root
    ):
        raise ValueError(
            "activation evidence manifest must be outside candidate and installed trees"
        )
    try:
        payload = json.loads(
            manifest_path.read_text(encoding="utf-8", errors="strict")
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid activation evidence manifest: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("activation evidence manifest must be a JSON object")
    if payload.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise ValueError(
            f"activation evidence schema_version must be {EVIDENCE_SCHEMA_VERSION!r}"
        )
    batch_id = required_text(payload, "batch_id", "manifest")
    if not valid_uuid(batch_id):
        raise ValueError("manifest.batch_id must be a canonical UUID")
    attested_at = required_text(payload, "attested_at", "manifest")
    if not strict_iso_datetime(attested_at):
        raise ValueError("manifest.attested_at must be an ISO timestamp with timezone")
    operator_id = required_text(payload, "operator_id", "manifest")
    reviewer_id = required_text(payload, "reviewer_id", "manifest")
    if operator_id.casefold() == reviewer_id.casefold():
        raise ValueError("manifest reviewer_id must differ from operator_id")
    model = required_text(payload, "model", "manifest")
    run_date = required_text(payload, "run_date", "manifest")
    if models != {model} or run_dates != {run_date}:
        raise ValueError("manifest model/run_date do not match activation results")
    if not strict_iso_date(run_date):
        raise ValueError("manifest.run_date must be YYYY-MM-DD")
    if required_sha256(payload, "golden_sha256", "manifest") != sha256_file(
        golden_path
    ):
        raise ValueError("manifest.golden_sha256 does not match the golden prompts")
    if required_sha256(payload, "results_sha256", "manifest") != sha256_file(
        results_path
    ):
        raise ValueError("manifest.results_sha256 does not match the results TSV")

    candidate = payload.get("candidate")
    if not isinstance(candidate, dict):
        raise ValueError("manifest.candidate must be an object")
    plugin_name = required_text(candidate, "plugin_name", "manifest.candidate")
    version = required_text(candidate, "version", "manifest.candidate")
    if plugin_name != plugin.get("name") or version != plugin.get("version"):
        raise ValueError("manifest candidate identity does not match plugin.json")
    declared_candidate_digest = required_sha256(
        candidate, "sha256s_sha256", "manifest.candidate"
    )
    if declared_candidate_digest != candidate_sha256s:
        raise ValueError("manifest candidate digest does not match candidate SHA256SUMS")

    installation = payload.get("installation")
    if not isinstance(installation, dict):
        raise ValueError("manifest.installation must be an object")
    receipt_id = required_text(installation, "receipt_id", "manifest.installation")
    if not valid_uuid(receipt_id):
        raise ValueError("manifest.installation.receipt_id must be a canonical UUID")
    installed_at = required_text(
        installation, "installed_at", "manifest.installation"
    )
    if not strict_iso_datetime(installed_at):
        raise ValueError(
            "manifest.installation.installed_at must be an ISO timestamp with timezone"
        )
    if not required_bool(installation, "fresh_install", "manifest.installation"):
        raise ValueError("manifest.installation.fresh_install must be true")
    for key in ("host_product", "host_version", "install_method"):
        required_text(installation, key, "manifest.installation")
    if required_sha256(
        installation,
        "candidate_sha256s_sha256",
        "manifest.installation",
    ) != candidate_sha256s:
        raise ValueError("installation receipt is not bound to the candidate")
    if required_sha256(
        installation,
        "installed_sha256s_sha256",
        "manifest.installation",
    ) != installed_sha256s:
        raise ValueError("installation receipt is not bound to the installed tree")

    sessions = payload.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        raise ValueError("manifest.sessions must be a non-empty array")
    indexed: dict[str, dict[str, Any]] = {}
    session_ids: set[str] = set()
    transcript_paths: set[str] = set()
    for index, session in enumerate(sessions):
        context = f"manifest.sessions[{index}]"
        if not isinstance(session, dict):
            raise ValueError(f"{context} must be an object")
        case_id = required_text(session, "case_id", context)
        if case_id in indexed:
            raise ValueError(f"duplicate evidence case_id {case_id!r}")
        session_id = required_text(session, "session_id", context)
        if not valid_uuid(session_id) or session_id in session_ids:
            raise ValueError(f"{context}.session_id must be a unique canonical UUID")
        session_ids.add(session_id)
        if not required_bool(session, "fresh_session", context):
            raise ValueError(f"{context}.fresh_session must be true")
        if case_id not in golden:
            raise ValueError(f"{context} references unknown case {case_id!r}")
        prompt_digest = required_sha256(session, "prompt_sha256", context)
        expected_prompt_digest = sha256_bytes(
            golden[case_id]["row"]["prompt"].encode("utf-8")
        )
        if prompt_digest != expected_prompt_digest:
            raise ValueError(f"{context}.prompt_sha256 does not match the golden prompt")
        relative_transcript = required_text(session, "transcript_path", context)
        if relative_transcript.casefold() in transcript_paths:
            raise ValueError(f"duplicate transcript_path {relative_transcript!r}")
        transcript_paths.add(relative_transcript.casefold())
        transcript = safe_relative_file(
            manifest_path.parent, relative_transcript, f"{context}.transcript_path"
        )
        transcript_digest = required_sha256(session, "transcript_sha256", context)
        if sha256_file(transcript) != transcript_digest:
            raise ValueError(f"{context}.transcript_sha256 mismatch")
        indexed[case_id] = session

    if set(indexed) != set(observed):
        missing = sorted(set(observed) - set(indexed))[:5]
        extra = sorted(set(indexed) - set(observed))[:5]
        raise ValueError(
            f"evidence sessions do not match results; missing={missing}, extra={extra}"
        )
    for case_id, row in observed.items():
        session = indexed[case_id]
        if row["session_id"].strip().lower() != required_text(
            session, "session_id", f"session {case_id}"
        ).lower():
            raise ValueError(f"{case_id}: session_id does not match evidence manifest")
        if row["transcript_path"].strip() != required_text(
            session, "transcript_path", f"session {case_id}"
        ):
            raise ValueError(f"{case_id}: transcript_path does not match evidence manifest")
        if row["transcript_sha256"].strip().lower() != required_sha256(
            session, "transcript_sha256", f"session {case_id}"
        ):
            raise ValueError(f"{case_id}: transcript_sha256 does not match evidence manifest")

    return {
        "manifest_sha256": sha256_file(manifest_path),
        "batch_id": batch_id,
        "receipt_id": receipt_id,
        "candidate_sha256s_sha256": candidate_sha256s,
        "installed_sha256s_sha256": installed_sha256s,
        "plugin_name": plugin_name,
        "version": version,
        "operator_id": operator_id,
        "reviewer_id": reviewer_id,
    }


def validate_thresholds(args: argparse.Namespace) -> str | None:
    inherited = {
        "min_skill_precision": args.min_precision,
        "min_skill_recall": args.min_recall,
        "min_class_exact_routing": args.min_exact_routing,
    }
    for name, default in inherited.items():
        if getattr(args, name) is None:
            setattr(args, name, default)
    for name in (
        "min_precision",
        "min_recall",
        "min_exact_routing",
        "min_skill_precision",
        "min_skill_recall",
        "min_class_exact_routing",
    ):
        value = getattr(args, name)
        if not 0.0 <= value <= 1.0:
            return (
                "--"
                + name.replace("_", "-")
                + " must be between 0 and 1"
            )
    return None


def fail_input(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 2


def main() -> int:
    configure_utf8_streams()
    args = parse_args()
    threshold_error = validate_thresholds(args)
    if threshold_error:
        return fail_input(threshold_error)
    try:
        golden_path = require_plain_file(
            args.golden.expanduser(), "golden prompts", nonempty=True
        ).resolve(strict=True)
        results_path = require_plain_file(
            args.results.expanduser(), "activation results", nonempty=True
        ).resolve(strict=True)
        candidate_input = args.candidate_root.expanduser()
        installed_input = args.installed_root.expanduser()
        candidate_root = candidate_input.resolve(strict=True)
        installed_root = installed_input.resolve(strict=True)
        if candidate_root == installed_root:
            raise ValueError("candidate and installed roots must be distinct")
        candidate_entries, candidate_sha256s, plugin = verify_release_tree(
            candidate_input
        )
        installed_entries, installed_sha256s, installed_plugin = verify_release_tree(
            installed_input
        )
        if candidate_entries != installed_entries:
            raise ValueError("installed file hashes do not match the release candidate")
        if candidate_sha256s != installed_sha256s:
            raise ValueError("installed SHA256SUMS does not match the release candidate")
        if installed_plugin.get("name") != plugin.get("name") or installed_plugin.get(
            "version"
        ) != plugin.get("version"):
            raise ValueError("installed Plugin identity does not match the candidate")
        golden_rows = read_tsv(golden_path, GOLDEN_COLUMNS)
        result_rows = read_tsv(results_path, RESULT_COLUMNS)
    except (OSError, UnicodeError, ValueError) as exc:
        return fail_input(str(exc))

    golden: dict[str, dict[str, Any]] = {}
    suite_skills: set[str] = set()
    for row_number, row in enumerate(golden_rows, start=2):
        case_id = row["id"].strip()
        if not case_id or case_id in golden:
            return fail_input(f"empty or duplicate golden case {case_id!r}")
        case_class = row["class"].strip()
        if case_class not in ALLOWED_CLASSES:
            return fail_input(
                f"{args.golden}:{row_number}: invalid class {case_class!r}"
            )
        expected = parse_skill_set(row["expected_skills"])
        forbidden = parse_skill_set(row["forbidden_skills"])
        if expected & forbidden:
            return fail_input(
                f"{case_id}: Skill cannot be both expected and forbidden"
            )
        target = row["target_skill"].strip()
        if not target:
            return fail_input(f"{case_id}: target_skill is required")
        suite_skills.add(target)
        suite_skills.update(expected)
        suite_skills.update(forbidden)
        golden[case_id] = {
            "row": row,
            "expected": expected,
            "forbidden": forbidden,
        }

    observed: dict[str, dict[str, str]] = {}
    models: set[str] = set()
    run_dates: set[str] = set()
    for row in result_rows:
        case_id = row["case_id"].strip()
        if not case_id or case_id in observed:
            return fail_input(f"empty or duplicate result case {case_id!r}")
        if case_id not in golden:
            return fail_input(f"result references unknown case {case_id!r}")
        model = row["model"].strip()
        run_date = row["run_date"].strip()
        if not model or not run_date:
            return fail_input(f"{case_id}: model and run_date are required")
        if not strict_iso_date(run_date):
            return fail_input(
                f"{case_id}: run_date must be an ISO calendar date YYYY-MM-DD"
            )
        session_id = row["session_id"].strip().lower()
        if not valid_uuid(session_id):
            return fail_input(f"{case_id}: session_id must be a canonical UUID")
        transcript_path = row["transcript_path"].strip()
        if not transcript_path:
            return fail_input(f"{case_id}: transcript_path is required")
        transcript_sha256 = row["transcript_sha256"].strip().lower()
        if SHA256_RE.fullmatch(transcript_sha256) is None:
            return fail_input(
                f"{case_id}: transcript_sha256 must be a lower-case SHA-256 digest"
            )
        models.add(model)
        run_dates.add(run_date)
        behavior = row["behavior_pass"].strip().lower()
        if behavior not in {"true", "false", "not-scored"}:
            return fail_input(
                f"{case_id}: behavior_pass must be true, false, or not-scored"
            )
        loaded = parse_skill_set(row["loaded_skills"])
        unknown = sorted(loaded - suite_skills)
        if unknown:
            return fail_input(
                f"{case_id}: loaded_skills contains unknown suite skills {unknown}"
            )
        observed[case_id] = row
    if len(models) > 1:
        return fail_input(
            f"all rows must use one model; found {sorted(models)}"
        )
    if len(run_dates) > 1:
        return fail_input(
            f"all rows must use one run_date; found {sorted(run_dates)}"
        )

    missing_results = sorted(set(golden) - set(observed))
    if missing_results and not args.allow_partial:
        return fail_input(
            f"missing {len(missing_results)} result row(s); "
            f"first: {missing_results[:5]}"
        )
    if not observed:
        return fail_input("no activation results to score")

    try:
        evidence = verify_evidence_manifest(
            manifest_path=args.evidence_manifest,
            golden_path=golden_path,
            results_path=results_path,
            candidate_root=candidate_root,
            installed_root=installed_root,
            candidate_sha256s=candidate_sha256s,
            installed_sha256s=installed_sha256s,
            plugin=plugin,
            golden=golden,
            observed=observed,
            models=models,
            run_dates=run_dates,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        return fail_input(str(exc))

    true_positive = {skill: 0 for skill in sorted(suite_skills)}
    false_positive = {skill: 0 for skill in sorted(suite_skills)}
    false_negative = {skill: 0 for skill in sorted(suite_skills)}
    forbidden_by_skill = {skill: 0 for skill in sorted(suite_skills)}
    cases: list[CaseResult] = []
    behavior_scored = 0
    behavior_passed = 0

    for case_id in sorted(observed):
        spec = golden[case_id]
        row = observed[case_id]
        expected: set[str] = spec["expected"]
        forbidden: set[str] = spec["forbidden"]
        loaded = parse_skill_set(row["loaded_skills"])
        missing = expected - loaded
        forbidden_activated = loaded & forbidden
        unexpected = (loaded - expected) | forbidden_activated
        for skill in suite_skills:
            if skill in expected and skill in loaded:
                true_positive[skill] += 1
            elif skill in expected:
                false_negative[skill] += 1
            elif skill in loaded:
                false_positive[skill] += 1
            if skill in forbidden_activated:
                forbidden_by_skill[skill] += 1
        behavior_raw = row["behavior_pass"].strip().lower()
        behavior_value = (
            None if behavior_raw == "not-scored" else behavior_raw == "true"
        )
        if behavior_value is not None:
            behavior_scored += 1
            behavior_passed += int(behavior_value)
        routing_pass = not missing and not unexpected
        overall_pass = routing_pass and behavior_value is True
        cases.append(
            CaseResult(
                case_id=case_id,
                case_class=spec["row"]["class"].strip(),
                expected=sorted(expected),
                forbidden=sorted(forbidden),
                loaded=sorted(loaded),
                missing=sorted(missing),
                unexpected=sorted(unexpected),
                forbidden_activated=sorted(forbidden_activated),
                behavior_pass=behavior_value,
                routing_pass=routing_pass,
                overall_pass=overall_pass,
            )
        )

    per_skill: dict[str, dict[str, float | int | bool]] = {}
    total_tp = total_fp = total_fn = 0
    per_skill_gate = True
    zero_recall_skills: list[str] = []
    for skill in sorted(suite_skills):
        tp = true_positive[skill]
        fp = false_positive[skill]
        fn = false_negative[skill]
        support = tp + fn
        precision = ratio(tp, tp + fp)
        recall = ratio(tp, support)
        skill_pass = (
            precision >= args.min_skill_precision
            and recall >= args.min_skill_recall
        )
        if support > 0 and recall == 0.0:
            zero_recall_skills.append(skill)
            skill_pass = False
        per_skill_gate = per_skill_gate and skill_pass
        total_tp += tp
        total_fp += fp
        total_fn += fn
        per_skill[skill] = {
            "support": support,
            "predicted": tp + fp,
            "true_positive": tp,
            "false_positive": fp,
            "false_negative": fn,
            "forbidden_activations": forbidden_by_skill[skill],
            "precision": precision,
            "recall": recall,
            "pass": skill_pass,
        }

    per_class: dict[str, dict[str, float | int | bool]] = {}
    per_class_gate = True
    for case_class in sorted(ALLOWED_CLASSES):
        class_cases = [
            case for case in cases if case.case_class == case_class
        ]
        exact = sum(case.routing_pass for case in class_cases)
        exact_rate = ratio(exact, len(class_cases))
        class_pass = (
            bool(class_cases)
            and exact_rate >= args.min_class_exact_routing
        )
        per_class_gate = per_class_gate and class_pass
        per_class[case_class] = {
            "cases": len(class_cases),
            "exact": exact,
            "exact_routing": exact_rate,
            "pass": class_pass,
        }

    micro_precision = ratio(total_tp, total_tp + total_fp)
    micro_recall = ratio(total_tp, total_tp + total_fn)
    exact_routing = ratio(
        sum(case.routing_pass for case in cases), len(cases)
    )
    behavior_rate = ratio(behavior_passed, behavior_scored)
    unscored_behavior = len(cases) - behavior_scored
    forbidden_activation_count = sum(
        len(case.forbidden_activated) for case in cases
    )
    partial = bool(missing_results)
    release_pass = (
        not partial
        and micro_precision >= args.min_precision
        and micro_recall >= args.min_recall
        and exact_routing >= args.min_exact_routing
        and per_skill_gate
        and per_class_gate
        and not zero_recall_skills
        and forbidden_activation_count == 0
        and unscored_behavior == 0
        and behavior_passed == behavior_scored
    )

    payload = {
        "model": next(iter(models)),
        "run_date": next(iter(run_dates)),
        "cases_scored": len(cases),
        "golden_cases": len(golden),
        "partial": partial,
        "release_eligible": not partial,
        "micro_precision": micro_precision,
        "micro_recall": micro_recall,
        "exact_routing": exact_routing,
        "behavior_pass_rate": behavior_rate,
        "unscored_behavior": unscored_behavior,
        "forbidden_activation_count": forbidden_activation_count,
        "zero_recall_skills": zero_recall_skills,
        "per_skill": per_skill,
        "per_class": per_class,
        "thresholds": {
            "min_precision": args.min_precision,
            "min_recall": args.min_recall,
            "min_exact_routing": args.min_exact_routing,
            "min_skill_precision": args.min_skill_precision,
            "min_skill_recall": args.min_skill_recall,
            "min_class_exact_routing": args.min_class_exact_routing,
        },
        "evidence": evidence,
        "pass": release_pass,
        "case_results": [asdict(case) for case in cases],
    }
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if partial:
            status = "DIAGNOSTIC ONLY"
        else:
            status = "RELEASE PASS" if release_pass else "RELEASE FAIL"
        print(
            f"RESULT: {status}; precision={micro_precision:.3f}; "
            f"recall={micro_recall:.3f}; exact-routing={exact_routing:.3f}; "
            f"behavior={behavior_rate:.3f}; "
            f"forbidden={forbidden_activation_count}; "
            f"cases={len(cases)}/{len(golden)}"
        )
        for case in cases:
            if not case.overall_pass:
                print(
                    f"CASE {case.case_id}: missing={case.missing} "
                    f"unexpected={case.unexpected} "
                    f"forbidden={case.forbidden_activated} "
                    f"behavior={case.behavior_pass}"
                )
    return 0 if release_pass else 1


if __name__ == "__main__":
    sys.exit(main())
