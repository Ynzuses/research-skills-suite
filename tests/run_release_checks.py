#!/usr/bin/env python3
"""Run suite checks with an external, hash-bound release trust policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import stat
import subprocess
import sys
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any


EXPECTED_SKILLS = (
    "evidence-traceable-literature-review",
    "reproducible-computational-research",
    "rigorous-research-workflow",
    "scientific-writing-and-revision",
)
POLICY_SCHEMA_VERSION = "1.0"
MINIMUM_THRESHOLDS = {
    "min_precision": 0.95,
    "min_recall": 0.90,
    "min_exact_routing": 0.90,
    "min_skill_precision": 0.95,
    "min_skill_recall": 0.90,
    "min_class_exact_routing": 0.90,
}


class ReleaseInputError(ValueError):
    """A release input or its approved identity is invalid."""


def configure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (AttributeError, OSError):
                pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Suite source root or exported Plugin candidate root.",
    )
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--deny-term", action="append", default=[])
    parser.add_argument("--allow-binary", action="append", default=[])
    parser.add_argument(
        "--trusted-root",
        type=Path,
        help="External suite source root containing the trusted release runner/tests.",
    )
    parser.add_argument(
        "--trust-policy",
        type=Path,
        help="External, maintainer-approved release trust policy.",
    )
    parser.add_argument(
        "--write-trust-policy-draft",
        type=Path,
        help="Write a new pending policy snapshot; performs no candidate code execution.",
    )
    parser.add_argument(
        "--official-validator",
        type=Path,
        help="External official quick_validate.py; run once for each Skill.",
    )
    parser.add_argument(
        "--plugin-validator",
        type=Path,
        help="External official validate_plugin.py for the public Plugin tree.",
    )
    parser.add_argument(
        "--activation-results",
        type=Path,
        help="External complete clean-session activation-results TSV.",
    )
    parser.add_argument(
        "--installed-root",
        type=Path,
        help="Separate clean installation of the exact release candidate.",
    )
    parser.add_argument(
        "--evidence-manifest",
        type=Path,
        help="External activation evidence manifest and transcript inventory.",
    )
    parser.add_argument("--min-precision", type=float, default=0.95)
    parser.add_argument("--min-recall", type=float, default=0.90)
    parser.add_argument("--min-exact-routing", type=float, default=0.90)
    parser.add_argument("--min-skill-precision", type=float, default=0.95)
    parser.add_argument("--min-skill-recall", type=float, default=0.90)
    parser.add_argument("--min-class-exact-routing", type=float, default=0.90)
    parser.add_argument(
        "--release",
        action="store_true",
        help="Request the hash-bound trusted technical release gate.",
    )
    return parser.parse_args()


def child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "PYTHONSTARTUP"):
        environment.pop(name, None)
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8:strict"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONNOUSERSITE"] = "1"
    return environment


def run_stage(
    label: str,
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
) -> bool:
    print(f"STAGE: {label}")
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=child_environment(),
            check=False,
            capture_output=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"STAGE ERROR: {label}: {exc}", file=sys.stderr)
        return False
    try:
        stdout = completed.stdout.decode("utf-8", errors="strict")
        stderr = completed.stderr.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        print(
            f"STAGE ERROR: {label}: child output is not strict UTF-8: {exc}",
            file=sys.stderr,
        )
        return False
    if stdout:
        print(stdout.rstrip())
    if stderr:
        destination = sys.stdout if completed.returncode == 0 else sys.stderr
        print(stderr.rstrip(), file=destination)
    result = "OK" if completed.returncode == 0 else "FAILED"
    print(f"STAGE RESULT: {label}: {result}")
    return completed.returncode == 0


def has_reparse_point(path: Path) -> bool:
    try:
        attributes = path.lstat().st_file_attributes
    except AttributeError:
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def stable_stat_key(value: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
        value.st_nlink,
    )


def sha256_file(path: Path) -> str:
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if stable_stat_key(before) != stable_stat_key(after):
        raise ReleaseInputError(f"file changed while hashing: {path}")
    return digest.hexdigest()


def regular_file(path: Path, label: str, *, nonempty: bool = True) -> Path:
    original = path.expanduser()
    try:
        metadata = original.lstat()
    except OSError as exc:
        raise ReleaseInputError(f"{label} is not readable: {original}: {exc}") from exc
    if original.is_symlink() or has_reparse_point(original):
        raise ReleaseInputError(f"{label} must not be a symlink or reparse point: {original}")
    if not stat.S_ISREG(metadata.st_mode):
        raise ReleaseInputError(f"{label} must be a regular file: {original}")
    if metadata.st_nlink != 1:
        raise ReleaseInputError(f"{label} must not be hard-linked: {original}")
    if nonempty and metadata.st_size == 0:
        raise ReleaseInputError(f"{label} must not be empty: {original}")
    return original.resolve(strict=True)


def regular_root(path: Path, label: str) -> Path:
    original = path.expanduser()
    try:
        metadata = original.lstat()
    except OSError as exc:
        raise ReleaseInputError(f"{label} is not readable: {original}: {exc}") from exc
    if original.is_symlink() or has_reparse_point(original):
        raise ReleaseInputError(f"{label} must not be a symlink or reparse point: {original}")
    if not stat.S_ISDIR(metadata.st_mode):
        raise ReleaseInputError(f"{label} must be a directory: {original}")
    return original.resolve(strict=True)


def file_identity(path: Path, label: str) -> dict[str, Any]:
    resolved = regular_file(path, label)
    return {"resolved_path": str(resolved), "sha256": sha256_file(resolved)}


def tree_identity(path: Path, label: str) -> dict[str, Any]:
    root = regular_root(path, label)
    records: list[tuple[str, str, str | None]] = []
    casefolded: dict[str, str] = {}
    file_count = 0
    directory_count = 0

    def fail_walk(exc: OSError) -> None:
        raise exc

    try:
        for parent, dirnames, filenames in os.walk(
            root, topdown=True, followlinks=False, onerror=fail_walk
        ):
            parent_path = Path(parent)
            dirnames.sort(key=str.casefold)
            filenames.sort(key=str.casefold)
            for name in dirnames:
                directory = parent_path / name
                metadata = directory.lstat()
                if directory.is_symlink() or has_reparse_point(directory):
                    raise ReleaseInputError(f"{label} contains linked directory: {directory}")
                if not stat.S_ISDIR(metadata.st_mode):
                    raise ReleaseInputError(f"{label} contains non-directory entry: {directory}")
                relative = directory.relative_to(root).as_posix()
                folded = relative.casefold()
                if folded in casefolded:
                    raise ReleaseInputError(
                        f"{label} contains case-colliding paths: "
                        f"{casefolded[folded]!r}, {relative!r}"
                    )
                casefolded[folded] = relative
                records.append(("D", relative, None))
                directory_count += 1
            for name in filenames:
                member = parent_path / name
                metadata = member.lstat()
                if member.is_symlink() or has_reparse_point(member):
                    raise ReleaseInputError(f"{label} contains linked file: {member}")
                if not stat.S_ISREG(metadata.st_mode):
                    raise ReleaseInputError(f"{label} contains non-regular file: {member}")
                if metadata.st_nlink != 1:
                    raise ReleaseInputError(f"{label} contains hard-linked file: {member}")
                relative = member.relative_to(root).as_posix()
                folded = relative.casefold()
                if folded in casefolded:
                    raise ReleaseInputError(
                        f"{label} contains case-colliding paths: "
                        f"{casefolded[folded]!r}, {relative!r}"
                    )
                casefolded[folded] = relative
                records.append(("F", relative, sha256_file(member)))
                file_count += 1
    except OSError as exc:
        raise ReleaseInputError(f"cannot scan {label}: {exc}") from exc

    digest = hashlib.sha256(b"release-tree-v1\0")
    for kind, relative, member_digest in sorted(
        records, key=lambda item: (item[1].encode("utf-8"), item[0])
    ):
        digest.update(kind.encode("ascii") + b"\0")
        digest.update(relative.encode("utf-8") + b"\0")
        if member_digest is not None:
            digest.update(member_digest.encode("ascii"))
        digest.update(b"\n")
    return {
        "resolved_path": str(root),
        "tree_sha256": digest.hexdigest(),
        "file_count": file_count,
        "directory_count": directory_count,
    }


def is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def ensure_disjoint_roots(named_roots: dict[str, Path]) -> None:
    items = list(named_roots.items())
    for index, (left_name, left) in enumerate(items):
        for right_name, right in items[index + 1 :]:
            if is_within(left, right) or is_within(right, left):
                raise ReleaseInputError(
                    f"release roots must be pairwise non-nested: "
                    f"{left_name}={left}; {right_name}={right}"
                )


def resolve_output_path(path: Path, label: str) -> Path:
    expanded = path.expanduser()
    if expanded.exists() or expanded.is_symlink():
        raise ReleaseInputError(f"{label} already exists: {expanded}")
    parent = regular_root(expanded.parent, f"{label} parent")
    return parent / expanded.name


def resolve_python(command: str) -> Path:
    located = shutil.which(command)
    if located is None:
        raise ReleaseInputError(f"Python interpreter was not found: {command!r}")
    return regular_file(Path(located), "Python interpreter")


def validate_thresholds(args: argparse.Namespace) -> dict[str, float]:
    values: dict[str, float] = {}
    for key, floor in MINIMUM_THRESHOLDS.items():
        value = getattr(args, key)
        if not isinstance(value, float) or not math.isfinite(value):
            raise ReleaseInputError(f"--{key.replace('_', '-')} must be finite")
        if not 0.0 <= value <= 1.0:
            raise ReleaseInputError(
                f"--{key.replace('_', '-')} must be between 0 and 1"
            )
        if value < floor:
            raise ReleaseInputError(
                f"--{key.replace('_', '-')}={value} is below release floor {floor}"
            )
        values[key] = value
    return values


def trusted_test_identity(trusted_root: Path) -> dict[str, Any]:
    tests_root = trusted_root / "tests"
    tests = sorted(tests_root.glob("test_*.py"), key=lambda value: value.name.casefold())
    if not tests:
        raise ReleaseInputError(f"trusted test set is empty: {tests_root}")
    entries: list[dict[str, str]] = []
    folded: set[str] = set()
    digest = hashlib.sha256(b"trusted-test-set-v1\0")
    for test in tests:
        identity = file_identity(test, "trusted regression test")
        relative = Path(identity["resolved_path"]).relative_to(trusted_root).as_posix()
        if relative.casefold() in folded:
            raise ReleaseInputError(f"trusted tests contain a case collision: {relative}")
        folded.add(relative.casefold())
        entries.append({"relative_path": relative, "sha256": identity["sha256"]})
    for entry in sorted(entries, key=lambda value: value["relative_path"].encode("utf-8")):
        digest.update(entry["relative_path"].encode("utf-8") + b"\0")
        digest.update(entry["sha256"].encode("ascii") + b"\n")
    return {
        "pattern": "tests/test_*.py",
        "count": len(entries),
        "set_sha256": digest.hexdigest(),
        "files": entries,
    }


def release_paths(
    args: argparse.Namespace, policy_path: Path, *, policy_is_output: bool = False
) -> tuple[dict[str, Path], dict[str, Path], Path]:
    candidate = regular_root(args.root, "candidate root")
    trusted = regular_root(args.trusted_root, "trusted source root")
    installed = regular_root(args.installed_root, "installed root")
    roots = {"candidate": candidate, "trusted": trusted, "installed": installed}
    ensure_disjoint_roots(roots)

    runner = regular_file(Path(__file__), "release runner")
    expected_runner = regular_file(
        trusted / "tests" / "run_release_checks.py", "trusted release runner"
    )
    if runner != expected_runner:
        raise ReleaseInputError(
            "--release must execute trusted-root/tests/run_release_checks.py "
            "from outside the candidate"
        )

    policy_identity_path = (
        policy_path
        if policy_is_output
        else regular_file(policy_path, "trust policy")
    )
    external = {
        "trust policy": policy_identity_path,
        "Skill validator": regular_file(args.official_validator, "official Skill validator"),
        "Plugin validator": regular_file(args.plugin_validator, "official Plugin validator"),
        "activation results": regular_file(args.activation_results, "activation results"),
        "evidence manifest": regular_file(args.evidence_manifest, "evidence manifest"),
    }
    for name, external_path in external.items():
        for root_name, root in roots.items():
            if is_within(external_path, root):
                raise ReleaseInputError(
                    f"{name} must be outside candidate, trusted, and installed roots; "
                    f"it is inside {root_name}: {external_path}"
                )
    values = list(external.items())
    for index, (left_name, left) in enumerate(values):
        for right_name, right in values[index + 1 :]:
            if left == right:
                raise ReleaseInputError(
                    f"release inputs must be distinct: {left_name} and {right_name}"
                )
    return roots, external, resolve_python(args.python)


def build_release_snapshot(
    args: argparse.Namespace,
    policy_path: Path,
    thresholds: dict[str, float],
    *,
    policy_is_output: bool = False,
) -> dict[str, Any]:
    roots, external, python_path = release_paths(
        args, policy_path, policy_is_output=policy_is_output
    )
    trusted = roots["trusted"]
    snapshot = {
        "candidate": tree_identity(roots["candidate"], "candidate root"),
        "installed": tree_identity(roots["installed"], "installed root"),
        "trusted_source": {
            "resolved_root": str(trusted),
            "runner": file_identity(
                trusted / "tests" / "run_release_checks.py", "trusted release runner"
            ),
            "validate_suite": file_identity(
                trusted / "tests" / "validate_suite.py", "trusted static validator"
            ),
            "score_activation_results": file_identity(
                trusted / "tests" / "score_activation_results.py",
                "trusted activation scorer",
            ),
            "golden_prompts": file_identity(
                trusted / "tests" / "golden-prompts.tsv", "trusted golden prompts"
            ),
            "trusted_tests": trusted_test_identity(trusted),
        },
        "runtime": {"python": file_identity(python_path, "Python interpreter")},
        "official_validators": {
            "skill": file_identity(external["Skill validator"], "official Skill validator"),
            "plugin": file_identity(
                external["Plugin validator"], "official Plugin validator"
            ),
        },
        "activation_evidence": {
            "results": file_identity(external["activation results"], "activation results"),
            "manifest": file_identity(external["evidence manifest"], "evidence manifest"),
        },
        "thresholds": thresholds,
    }
    candidate_identity = snapshot["candidate"]
    installed_identity = snapshot["installed"]
    for key in ("tree_sha256", "file_count", "directory_count"):
        if candidate_identity[key] != installed_identity[key]:
            raise ReleaseInputError(
                "installed tree must be an exact content-and-layout copy of the candidate"
            )
    return snapshot


def pending_policy(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": POLICY_SCHEMA_VERSION,
        "status": "pending",
        "approval": {"approver": "PENDING", "approved_at": "PENDING"},
        **snapshot,
    }


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseInputError(f"trust policy contains duplicate key: {key!r}")
        result[key] = value
    return result


def reject_nonfinite(value: str) -> Any:
    raise ReleaseInputError(f"trust policy contains non-finite number: {value}")


def load_policy(path: Path) -> tuple[dict[str, Any], str]:
    resolved = regular_file(path, "trust policy")
    raw = resolved.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        text = raw.decode("utf-8", errors="strict")
        payload = json.loads(
            text,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite,
        )
    except UnicodeError as exc:
        raise ReleaseInputError(f"trust policy is not strict UTF-8: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ReleaseInputError(f"trust policy is invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ReleaseInputError("trust policy must be a JSON object")
    return payload, digest


def strict_timezone_timestamp(value: str) -> bool:
    if not isinstance(value, str) or not value.strip() or value == "PENDING":
        return False
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return "T" in value and parsed.tzinfo is not None and parsed.utcoffset() is not None


def first_difference(actual: Any, expected: Any, path: str) -> str | None:
    if type(actual) is not type(expected):
        if not (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and isinstance(expected, (int, float))
            and not isinstance(expected, bool)
            and actual == expected
        ):
            return f"{path} has wrong type/value"
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            actual_keys = sorted(actual) if isinstance(actual, dict) else []
            return f"{path} keys differ; expected={sorted(expected)}, actual={actual_keys}"
        for key in expected:
            mismatch = first_difference(actual[key], expected[key], f"{path}.{key}")
            if mismatch:
                return mismatch
        return None
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return f"{path} length differs"
        for index, value in enumerate(expected):
            mismatch = first_difference(actual[index], value, f"{path}[{index}]")
            if mismatch:
                return mismatch
        return None
    if actual != expected:
        return f"{path} does not match the current trusted identity"
    return None


def validate_approved_policy(
    policy: dict[str, Any], snapshot: dict[str, Any]
) -> None:
    expected_keys = {"schema_version", "status", "approval", *snapshot.keys()}
    if set(policy) != expected_keys:
        raise ReleaseInputError(
            f"trust policy keys differ; expected={sorted(expected_keys)}, "
            f"actual={sorted(policy)}"
        )
    if policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        raise ReleaseInputError(
            f"trust policy schema_version must be {POLICY_SCHEMA_VERSION!r}"
        )
    if policy.get("status") != "approved":
        raise ReleaseInputError("trust policy status must be 'approved'")
    approval = policy.get("approval")
    if not isinstance(approval, dict) or set(approval) != {"approver", "approved_at"}:
        raise ReleaseInputError("trust policy approval must contain approver and approved_at")
    approver = approval.get("approver")
    if (
        not isinstance(approver, str)
        or not approver.strip()
        or approver.strip().casefold() == "pending"
    ):
        raise ReleaseInputError("trust policy approver must identify the human approver")
    if not strict_timezone_timestamp(approval.get("approved_at")):
        raise ReleaseInputError(
            "trust policy approved_at must be an ISO timestamp with timezone"
        )
    for key, expected in snapshot.items():
        mismatch = first_difference(policy.get(key), expected, f"policy.{key}")
        if mismatch:
            raise ReleaseInputError(mismatch)


def write_policy_draft(path: Path, snapshot: dict[str, Any]) -> None:
    serialized = json.dumps(pending_policy(snapshot), ensure_ascii=False, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8", errors="strict", newline="\n") as handle:
            handle.write(serialized)
    except OSError as exc:
        raise ReleaseInputError(f"cannot write trust policy draft: {path}: {exc}") from exc


class ReleaseGuard:
    def __init__(
        self,
        args: argparse.Namespace,
        policy_path: Path,
        policy_sha256: str,
        snapshot: dict[str, Any],
        thresholds: dict[str, float],
    ) -> None:
        self.args = args
        self.policy_path = policy_path
        self.policy_sha256 = policy_sha256
        self.snapshot = snapshot
        self.thresholds = thresholds

    def verify(self, moment: str) -> None:
        current_policy = file_identity(self.policy_path, "trust policy")
        if current_policy["sha256"] != self.policy_sha256:
            raise ReleaseInputError(f"trust policy changed {moment}")
        current = build_release_snapshot(self.args, self.policy_path, self.thresholds)
        mismatch = first_difference(current, self.snapshot, "release identity")
        if mismatch:
            raise ReleaseInputError(f"{mismatch} ({moment})")


def run_guarded_stage(
    guard: ReleaseGuard,
    label: str,
    command: list[str],
    *,
    cwd: Path,
    timeout: int,
) -> bool:
    try:
        guard.verify(f"before stage {label!r}")
    except (OSError, ReleaseInputError) as exc:
        print(f"TRUST ERROR: {exc}", file=sys.stderr)
        return False
    stage_pass = run_stage(label, command, cwd=cwd, timeout=timeout)
    try:
        guard.verify(f"after stage {label!r}")
    except (OSError, ReleaseInputError) as exc:
        print(f"TRUST ERROR: {exc}", file=sys.stderr)
        return False
    return stage_pass


def skill_root(root: Path) -> Path:
    nested = root / "skills"
    if all((nested / name / "SKILL.md").is_file() for name in EXPECTED_SKILLS):
        return nested
    return root


def python_command(python_path: Path, *arguments: str) -> list[str]:
    return [str(python_path), "-I", "-B", *arguments]


@contextmanager
def owned_temporary_directory(parent: Path, prefix: str):
    """Create a same-volume temporary directory without restrictive Windows ACLs."""
    parent = regular_root(parent, "temporary-directory parent")
    target = parent / f"{prefix}{uuid.uuid4().hex}"
    target.mkdir()
    try:
        yield target
    finally:
        resolved_parent = target.parent.resolve(strict=True)
        if resolved_parent != parent:
            raise ReleaseInputError(
                f"temporary cleanup target escaped its approved parent: {target}"
            )
        shutil.rmtree(target)


def prepare_trusted_test_mirror(
    candidate: Path,
    trusted: Path,
    baseline: dict[str, Any],
    temporary_root: Path,
) -> Path:
    mirror = temporary_root / "candidate-mirror"
    shutil.copytree(candidate, mirror, symlinks=True)
    copied = tree_identity(mirror, "isolated candidate mirror")
    for key in ("tree_sha256", "file_count", "directory_count"):
        if copied[key] != baseline[key]:
            raise ReleaseInputError("isolated candidate mirror does not match candidate")
    mirror_tests = mirror / "tests"
    if mirror_tests.exists():
        shutil.rmtree(mirror_tests)
    mirror_tests.mkdir(parents=True)
    trusted_tests = trusted_test_identity(trusted)
    relative_files = [entry["relative_path"] for entry in trusted_tests["files"]]
    relative_files.extend(
        (
            "tests/run_release_checks.py",
            "tests/validate_suite.py",
            "tests/score_activation_results.py",
            "tests/golden-prompts.tsv",
        )
    )
    for relative in sorted(set(relative_files)):
        source = trusted.joinpath(*relative.split("/"))
        destination = mirror.joinpath(*relative.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        if sha256_file(source) != sha256_file(destination):
            raise ReleaseInputError(f"trusted test overlay copy mismatch: {relative}")
    return mirror


def prepare_untrusted_test_mirror(
    root: Path, skills: Path, temporary_root: Path
) -> Path:
    if skills == root:
        mirror = temporary_root / "source-mirror"
        shutil.copytree(root, mirror, symlinks=True)
        return mirror
    mirror = temporary_root / f"flat-{uuid.uuid4().hex}"
    mirror.mkdir()
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if path.is_file() and path.name not in {"RELEASE_MANIFEST.json", "SHA256SUMS"}:
            shutil.copyfile(path, mirror / path.name)
    for directory_name in ("tests", "scripts"):
        source = root / directory_name
        if source.is_dir():
            shutil.copytree(
                source,
                mirror / directory_name,
                symlinks=True,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )
    for name in EXPECTED_SKILLS:
        shutil.copytree(skills / name, mirror / name, symlinks=True)
    return mirror


def print_release_identities(
    snapshot: dict[str, Any], policy_path: Path, policy_sha256: str
) -> None:
    print(
        "IDENTITY: candidate "
        f"path={snapshot['candidate']['resolved_path']} "
        f"tree_sha256={snapshot['candidate']['tree_sha256']}"
    )
    print(
        "IDENTITY: installed "
        f"path={snapshot['installed']['resolved_path']} "
        f"tree_sha256={snapshot['installed']['tree_sha256']}"
    )
    print(f"IDENTITY: trust_policy path={policy_path} sha256={policy_sha256}")
    trusted = snapshot["trusted_source"]
    print(
        "IDENTITY: trusted_runner "
        f"path={trusted['runner']['resolved_path']} sha256={trusted['runner']['sha256']}"
    )
    print(
        "IDENTITY: trusted_tests "
        f"count={trusted['trusted_tests']['count']} "
        f"set_sha256={trusted['trusted_tests']['set_sha256']}"
    )
    for label, key in (
        ("trusted_static", "validate_suite"),
        ("trusted_scorer", "score_activation_results"),
        ("golden", "golden_prompts"),
    ):
        print(
            f"IDENTITY: {label} path={trusted[key]['resolved_path']} "
            f"sha256={trusted[key]['sha256']}"
        )
    validators = snapshot["official_validators"]
    for name in ("skill", "plugin"):
        print(
            f"IDENTITY: {name}_validator path={validators[name]['resolved_path']} "
            f"sha256={validators[name]['sha256']}"
        )
    evidence = snapshot["activation_evidence"]
    for name in ("results", "manifest"):
        print(
            f"IDENTITY: activation_{name} path={evidence[name]['resolved_path']} "
            f"sha256={evidence[name]['sha256']}"
        )


def fail_summary(release: bool) -> int:
    print(
        "RESULT: TRUSTED TECHNICAL RELEASE GATE FAIL"
        if release
        else "RESULT: CHECKS FAILED"
    )
    return 1


def require_release_arguments(args: argparse.Namespace, *, draft: bool) -> None:
    required = {
        "--trusted-root": args.trusted_root,
        "--official-validator": args.official_validator,
        "--plugin-validator": args.plugin_validator,
        "--activation-results": args.activation_results,
        "--installed-root": args.installed_root,
        "--evidence-manifest": args.evidence_manifest,
    }
    if not draft:
        required["--trust-policy"] = args.trust_policy
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ReleaseInputError(
            ("policy drafting" if draft else "--release")
            + " requires "
            + ", ".join(missing)
        )


def release_main(args: argparse.Namespace) -> int:
    require_release_arguments(args, draft=False)
    thresholds = validate_thresholds(args)
    policy_path = regular_file(args.trust_policy, "trust policy")
    snapshot = build_release_snapshot(args, policy_path, thresholds)
    policy, policy_sha256 = load_policy(policy_path)
    validate_approved_policy(policy, snapshot)
    guard = ReleaseGuard(args, policy_path, policy_sha256, snapshot, thresholds)
    candidate = Path(snapshot["candidate"]["resolved_path"])
    trusted = Path(snapshot["trusted_source"]["resolved_root"])
    installed = Path(snapshot["installed"]["resolved_path"])
    python_path = Path(snapshot["runtime"]["python"]["resolved_path"])
    skills = skill_root(candidate)
    if skills == candidate:
        raise ReleaseInputError("release gate requires the public root/skills layout")

    print_release_identities(snapshot, policy_path, policy_sha256)
    static_command = python_command(
        python_path,
        str(Path(snapshot["trusted_source"]["validate_suite"]["resolved_path"])),
        "--root",
        str(candidate),
    )
    for term in args.deny_term:
        static_command.extend(("--deny-term", term))
    for path in args.allow_binary:
        static_command.extend(("--allow-binary", path))
    if not run_guarded_stage(
        guard,
        "trusted dependency-free static checks",
        static_command,
        cwd=trusted,
        timeout=args.timeout,
    ):
        return fail_summary(True)

    try:
        with owned_temporary_directory(
            policy_path.parent, ".research-skills-release-"
        ) as temporary:
            mirror = prepare_trusted_test_mirror(
                candidate, trusted, snapshot["candidate"], temporary
            )
            if not run_guarded_stage(
                guard,
                "trusted regression tests on isolated candidate mirror",
                python_command(
                    python_path,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    str(mirror / "tests"),
                    "-p",
                    "test_*.py",
                ),
                cwd=mirror,
                timeout=args.timeout,
            ):
                return fail_summary(True)
    except (OSError, shutil.Error, ReleaseInputError) as exc:
        print(f"ERROR: cannot prepare trusted test mirror: {exc}", file=sys.stderr)
        return fail_summary(True)

    skill_validator = snapshot["official_validators"]["skill"]["resolved_path"]
    for name in EXPECTED_SKILLS:
        if not run_guarded_stage(
            guard,
            f"approved official Skill validator: {name}",
            python_command(python_path, skill_validator, str(skills / name)),
            cwd=trusted,
            timeout=args.timeout,
        ):
            return fail_summary(True)

    plugin_validator = snapshot["official_validators"]["plugin"]["resolved_path"]
    if not run_guarded_stage(
        guard,
        "approved official Plugin validator",
        python_command(python_path, plugin_validator, str(candidate)),
        cwd=trusted,
        timeout=args.timeout,
    ):
        return fail_summary(True)

    activation_command = python_command(
        python_path,
        snapshot["trusted_source"]["score_activation_results"]["resolved_path"],
        "--golden",
        snapshot["trusted_source"]["golden_prompts"]["resolved_path"],
        "--results",
        snapshot["activation_evidence"]["results"]["resolved_path"],
        "--candidate-root",
        str(candidate),
        "--installed-root",
        str(installed),
        "--evidence-manifest",
        snapshot["activation_evidence"]["manifest"]["resolved_path"],
        "--format",
        "json",
    )
    for key, value in thresholds.items():
        activation_command.extend(("--" + key.replace("_", "-"), str(value)))
    if not run_guarded_stage(
        guard,
        "approved clean-install activation scorer",
        activation_command,
        cwd=trusted,
        timeout=args.timeout,
    ):
        return fail_summary(True)

    print(
        "NOTICE: the trust policy is an auditable approval record, not a "
        "cryptographic signature or authorization to publish."
    )
    print("RESULT: TRUSTED TECHNICAL RELEASE GATE PASS")
    return 0


def draft_main(args: argparse.Namespace) -> int:
    require_release_arguments(args, draft=True)
    thresholds = validate_thresholds(args)
    output = resolve_output_path(args.write_trust_policy_draft, "trust policy draft")
    snapshot = build_release_snapshot(
        args, output, thresholds, policy_is_output=True
    )
    candidate = Path(snapshot["candidate"]["resolved_path"])
    if skill_root(candidate) == candidate:
        raise ReleaseInputError("policy drafting requires the public root/skills layout")
    write_policy_draft(output, snapshot)
    print_release_identities(snapshot, output, sha256_file(output))
    print(
        "RESULT: TRUST POLICY DRAFT WRITTEN (PENDING HUMAN REVIEW; "
        "NOT A DIGITAL SIGNATURE)"
    )
    return 0


def nonrelease_main(args: argparse.Namespace) -> int:
    root = regular_root(args.root, "root")
    python_path = resolve_python(args.python)
    static_command = python_command(
        python_path, str(root / "tests" / "validate_suite.py"), "--root", str(root)
    )
    for term in args.deny_term:
        static_command.extend(("--deny-term", term))
    for path in args.allow_binary:
        static_command.extend(("--allow-binary", path))
    if not run_stage(
        "dependency-free static checks",
        static_command,
        cwd=root,
        timeout=args.timeout,
    ):
        return fail_summary(False)

    skills = skill_root(root)
    try:
        with owned_temporary_directory(
            root.parent, ".research-skills-selftest-"
        ) as temporary:
            unittest_root = prepare_untrusted_test_mirror(root, skills, temporary)
            unittest_pass = run_stage(
                "candidate self-tests (non-trust evidence only)",
                python_command(
                    python_path,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    str(unittest_root / "tests"),
                    "-p",
                    "test_*.py",
                ),
                cwd=unittest_root,
                timeout=args.timeout,
            )
    except (OSError, shutil.Error, ReleaseInputError) as exc:
        print(f"ERROR: cannot prepare self-test mirror: {exc}", file=sys.stderr)
        return fail_summary(False)
    if not unittest_pass:
        return fail_summary(False)
    print("RESULT: CHECKS COMPLETE (no trusted release verdict)")
    return 0


def main() -> int:
    configure_utf8_streams()
    args = parse_args()
    if args.timeout <= 0:
        print("ERROR: --timeout must be positive", file=sys.stderr)
        return 2
    if args.release and args.write_trust_policy_draft is not None:
        print(
            "ERROR: --release and --write-trust-policy-draft are mutually exclusive",
            file=sys.stderr,
        )
        return 2
    if args.trust_policy is not None and not args.release:
        print("ERROR: --trust-policy is valid only with --release", file=sys.stderr)
        return 2
    try:
        if args.release:
            return release_main(args)
        if args.write_trust_policy_draft is not None:
            return draft_main(args)
        return nonrelease_main(args)
    except (OSError, ReleaseInputError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.release:
            print("RESULT: TRUSTED TECHNICAL RELEASE GATE FAIL")
        return 2


if __name__ == "__main__":
    sys.exit(main())
