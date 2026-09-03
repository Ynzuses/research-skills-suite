#!/usr/bin/env python3
"""Deterministically export the flat suite source as a public Plugin tree."""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


EXPECTED_SKILLS = (
    "evidence-traceable-literature-review",
    "genomics-study-design",
    "genotype-imputation-benchmarking",
    "manage-workspace-memory",
    "reproducible-computational-research",
    "research-document-delivery",
    "rigorous-research-workflow",
    "scientific-writing-and-revision",
)
REQUIRED_ROOT_FILES = (
    "CHANGELOG.md",
    "LICENSE",
    "MARKET_POSITION.md",
    "NOTICE",
    "PRIVACY.md",
    "PROVENANCE.md",
    "README.md",
    "TERMS.md",
    "TESTING.md",
    "VERSION",
)
OPTIONAL_PUBLIC_ROOT_FILES = (
    ".gitattributes",
    ".gitignore",
    "BINARY_ALLOWLIST.txt",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
)
IGNORED_DIR_NAMES = {
    ".cache",
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "cache",
    "dist",
    "env",
    "node_modules",
    "venv",
}
FORBIDDEN_INTERNAL_PREFIXES = (
    ".activation-",
    ".release-runner-",
    ".test-",
)
PLUGIN_NAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?")
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")
PLACEHOLDER_RE = re.compile(
    r"(?:\bTODO\b|\bTBD\b|placeholder|example\.com|"
    r"your[-_ ](?:name|org|url)|local developer|change[-_ ]?me)",
    re.IGNORECASE,
)
DEFAULT_KEYWORDS = (
    "research",
    "reproducibility",
    "literature-review",
    "scientific-writing",
    "workflow",
)
PRIVATE_DIRECTORY_MODE = 0o777 if os.name == "nt" else 0o700
PRIVATE_FILE_MODE = 0o666 if os.name == "nt" else 0o600


class ExportError(ValueError):
    pass


@dataclass(frozen=True)
class PathIdentity:
    device: int
    inode: int
    file_type: int


@dataclass(frozen=True)
class FileSnapshot:
    identity: PathIdentity
    size: int
    mtime_ns: int


@dataclass(frozen=True)
class CopyItem:
    source: Path
    destination: Path
    snapshot: FileSnapshot


@dataclass(frozen=True)
class AssembledFile:
    relative: str
    snapshot: FileSnapshot
    sha256: str


@dataclass(frozen=True)
class AssemblyPlan:
    """Externally held record of the bytes and inode written by assembly."""

    root_identity: PathIdentity
    files: tuple[AssembledFile, ...]


@dataclass(frozen=True)
class SourceValidation:
    version: str
    root_identity: PathIdentity
    directory_guards: tuple[tuple[Path, PathIdentity], ...]
    root_files: tuple[tuple[str, FileSnapshot], ...]


@dataclass(frozen=True)
class StagingOwnership:
    staging: Path
    staging_identity: PathIdentity
    marker: Path
    marker_snapshot: FileSnapshot
    token: str
    parent: Path
    parent_identity: PathIdentity


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
        "--source",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Current flat suite source root.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--plugin-name",
        default="research-skills-suite",
    )
    parser.add_argument("--author-name", required=True)
    parser.add_argument("--author-url", required=True)
    parser.add_argument("--repository-url", required=True)
    parser.add_argument("--homepage-url", required=True)
    parser.add_argument("--support-url", required=True)
    parser.add_argument("--privacy-policy-url", required=True)
    parser.add_argument("--terms-of-service-url", required=True)
    parser.add_argument("--license", required=True)
    parser.add_argument("--description", required=True)
    parser.add_argument(
        "--display-name",
        default="Research Skills Suite",
    )
    parser.add_argument("--category", default="Productivity")
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="Plugin discovery keyword; repeat as needed.",
    )
    parser.add_argument(
        "--expected-version",
        help="Fail unless this equals the source VERSION.",
    )
    return parser.parse_args()


def require_real_text(label: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ExportError(f"{label} must not be empty")
    if PLACEHOLDER_RE.search(cleaned):
        raise ExportError(f"{label} contains placeholder metadata")
    return cleaned


def require_https_url(label: str, value: str) -> str:
    cleaned = require_real_text(label, value)
    parsed = urlsplit(cleaned)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ExportError(f"{label} must be an absolute https URL without credentials")
    return cleaned


def lexical_absolute(path: Path) -> Path:
    """Return an absolute path without resolving links or reparse points."""

    return Path(os.path.abspath(os.fspath(path.expanduser())))


def path_exists_no_follow(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _identity_from_stat(
    result: os.stat_result,
    path: Path,
    expected_kind: str,
) -> PathIdentity:
    file_type = stat.S_IFMT(result.st_mode)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    file_attributes = getattr(result, "st_file_attributes", 0)
    is_junction = getattr(os.path, "isjunction", lambda _path: False)
    if (
        stat.S_ISLNK(result.st_mode)
        or bool(file_attributes & reparse_flag)
        or bool(is_junction(path))
    ):
        raise ExportError(f"links, junctions, and reparse points are forbidden: {path}")
    if expected_kind == "directory" and not stat.S_ISDIR(result.st_mode):
        raise ExportError(f"expected a real directory: {path}")
    if expected_kind == "file" and not stat.S_ISREG(result.st_mode):
        raise ExportError(f"expected a real regular file: {path}")
    link_count = int(getattr(result, "st_nlink", 1))
    if expected_kind == "file" and link_count != 1:
        raise ExportError(f"hard-linked files are forbidden: {path}")
    if expected_kind == "directory" and os.name == "nt" and link_count not in (0, 1):
        raise ExportError(f"hard-linked directories are forbidden: {path}")
    identity = PathIdentity(int(result.st_dev), int(result.st_ino), file_type)
    if identity.inode == 0:
        raise ExportError(f"filesystem identity is unavailable: {path}")
    return identity


def real_directory_identity(path: Path) -> PathIdentity:
    try:
        result = os.lstat(path)
    except OSError as exc:
        raise ExportError(f"cannot inspect directory {path}: {exc}") from exc
    return _identity_from_stat(result, path, "directory")


def real_file_snapshot(path: Path) -> FileSnapshot:
    try:
        result = os.lstat(path)
    except OSError as exc:
        raise ExportError(f"cannot inspect file {path}: {exc}") from exc
    return FileSnapshot(
        identity=_identity_from_stat(result, path, "file"),
        size=int(result.st_size),
        mtime_ns=int(result.st_mtime_ns),
    )


def reject_linked_directory_components(path: Path) -> None:
    absolute = lexical_absolute(path)
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        real_directory_identity(current)


def verify_directory_identity(path: Path, expected: PathIdentity) -> None:
    current = real_directory_identity(path)
    if current != expected:
        raise ExportError(f"directory identity changed during export: {path}")


def guarded_read_bytes(path: Path, expected: FileSnapshot) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ExportError(f"cannot open source file without following links: {path}: {exc}") from exc
    try:
        opened = os.fstat(descriptor)
        opened_snapshot = FileSnapshot(
            identity=_identity_from_stat(opened, path, "file"),
            size=int(opened.st_size),
            mtime_ns=int(opened.st_mtime_ns),
        )
        if opened_snapshot != expected:
            raise ExportError(f"source file identity changed before read: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after_read = os.fstat(descriptor)
        after_snapshot = FileSnapshot(
            identity=_identity_from_stat(after_read, path, "file"),
            size=int(after_read.st_size),
            mtime_ns=int(after_read.st_mtime_ns),
        )
        if after_snapshot != expected:
            raise ExportError(f"source file changed while being read: {path}")
    finally:
        os.close(descriptor)
    if real_file_snapshot(path) != expected:
        raise ExportError(f"source file path changed after read: {path}")
    return b"".join(chunks)


def exclusive_create_file(path: Path, data: bytes) -> FileSnapshot:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_BINARY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags, PRIVATE_FILE_MODE)
    except OSError as exc:
        raise ExportError(f"cannot exclusively create candidate file {path}: {exc}") from exc
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write while creating candidate file")
            view = view[written:]
        os.fsync(descriptor)
        result = os.fstat(descriptor)
        snapshot = FileSnapshot(
            identity=_identity_from_stat(result, path, "file"),
            size=int(result.st_size),
            mtime_ns=int(result.st_mtime_ns),
        )
    finally:
        os.close(descriptor)
    current = real_file_snapshot(path)
    if current.identity != snapshot.identity or current.size != len(data):
        raise ExportError(f"candidate file identity changed after creation: {path}")
    return current


def ignored_directory(name: str) -> bool:
    return name.casefold() in {item.casefold() for item in IGNORED_DIR_NAMES}


def forbidden_internal_name(name: str) -> bool:
    folded = name.casefold()
    return folded.startswith(
        tuple(item.casefold() for item in FORBIDDEN_INTERNAL_PREFIXES)
    )


def inspect_source_entry(path: Path) -> os.stat_result:
    """Audit an entry before any name-based exclusion is considered."""

    try:
        result = os.lstat(path)
    except OSError as exc:
        raise ExportError(f"cannot inspect source entry {path}: {exc}") from exc
    file_attributes = getattr(result, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    is_junction = getattr(os.path, "isjunction", lambda _path: False)
    if (
        stat.S_ISLNK(result.st_mode)
        or bool(file_attributes & reparse_flag)
        or bool(is_junction(path))
    ):
        raise ExportError(
            f"links, junctions, and reparse points are forbidden: {path}"
        )
    return result


def collect_tree_files(root: Path) -> list[tuple[Path, FileSnapshot]]:
    files: list[tuple[Path, FileSnapshot]] = []

    def visit(directory: Path) -> None:
        entries = sorted(
            os.scandir(directory),
            key=lambda item: (item.name.casefold(), item.name),
        )
        folded_names: set[str] = set()
        for entry in entries:
            folded_name = entry.name.casefold()
            if folded_name in folded_names:
                raise ExportError(
                    "case-insensitive path collision in source tree: "
                    f"{Path(entry.path).relative_to(root)}"
                )
            folded_names.add(folded_name)
            path = Path(entry.path)
            result = inspect_source_entry(path)
            if forbidden_internal_name(entry.name):
                raise ExportError(
                    "source tree contains an internal temporary path; remove it "
                    f"before export: {path.relative_to(root)}"
                )
            if ignored_directory(entry.name):
                _identity_from_stat(result, path, "directory")
                continue
            if stat.S_ISDIR(result.st_mode):
                _identity_from_stat(result, path, "directory")
                visit(path)
            elif stat.S_ISREG(result.st_mode):
                if entry.name.casefold().endswith((".pyc", ".pyo")):
                    continue
                files.append(
                    (
                        path,
                        FileSnapshot(
                            identity=_identity_from_stat(result, path, "file"),
                            size=int(result.st_size),
                            mtime_ns=int(result.st_mtime_ns),
                        ),
                    )
                )
            else:
                _identity_from_stat(result, path, "file")
                raise ExportError(
                    f"unsupported filesystem entry: {path.relative_to(root)}"
                )

    real_directory_identity(root)
    visit(root)
    return sorted(files, key=lambda item: item[0].relative_to(root).as_posix())


def validate_source(
    source: Path,
    expected_version: str | None,
) -> SourceValidation:
    reject_linked_directory_components(source)
    root_identity = real_directory_identity(source)
    try:
        root_entries = sorted(
            os.scandir(source),
            key=lambda item: (item.name.casefold(), item.name),
        )
    except OSError as exc:
        raise ExportError(f"cannot enumerate source root {source}: {exc}") from exc
    entries_by_folded_name: dict[str, str] = {}
    root_results: dict[str, os.stat_result] = {}
    for entry in root_entries:
        folded = entry.name.casefold()
        if folded in entries_by_folded_name:
            raise ExportError(
                "case-insensitive path collision in source root: "
                f"{entries_by_folded_name[folded]!r} and {entry.name!r}"
            )
        entries_by_folded_name[folded] = entry.name
        path = Path(entry.path)
        result = inspect_source_entry(path)
        root_results[entry.name] = result
        if forbidden_internal_name(entry.name):
            raise ExportError(
                "source root contains an internal temporary path; remove it "
                f"before export: {entry.name}"
            )
        if ignored_directory(entry.name):
            _identity_from_stat(result, path, "directory")

    def require_exact_name(name: str) -> Path:
        actual = entries_by_folded_name.get(name.casefold())
        if actual is None:
            raise ExportError(f"missing required source entry: {name}")
        if actual != name:
            raise ExportError(
                f"required source entry has non-canonical case: {actual!r}; expected {name!r}"
            )
        return source / actual

    directory_guards: list[tuple[Path, PathIdentity]] = []
    expected = set(EXPECTED_SKILLS)
    found: set[str] = set()
    for skill in EXPECTED_SKILLS:
        skill_root = require_exact_name(skill)
        directory_guards.append((skill_root, real_directory_identity(skill_root)))
        real_file_snapshot(skill_root / "SKILL.md")
        found.add(skill)

    for entry in root_entries:
        if entry.name in expected or entry.name in {"tests", "scripts"}:
            continue
        if ignored_directory(entry.name):
            continue
        path = Path(entry.path)
        result = root_results[entry.name]
        if stat.S_ISDIR(result.st_mode):
            _identity_from_stat(result, path, "directory")
            skill_marker = path / "SKILL.md"
            if path_exists_no_follow(skill_marker):
                real_file_snapshot(skill_marker)
                found.add(entry.name)
    if found != expected:
        raise ExportError(
            "flat source must contain exactly the declared 8 Skills; "
            f"missing={sorted(expected - found)}, extra={sorted(found - expected)}"
        )

    nested_root = source / "skills"
    if path_exists_no_follow(nested_root):
        real_directory_identity(nested_root)
        for nested_entry in os.scandir(nested_root):
            nested_path = Path(nested_entry.path)
            try:
                nested_result = os.lstat(nested_path)
            except OSError as exc:
                raise ExportError(f"cannot inspect nested source entry {nested_path}: {exc}") from exc
            if stat.S_ISDIR(nested_result.st_mode) and path_exists_no_follow(
                nested_path / "SKILL.md"
            ):
                raise ExportError("source is an ambiguous nested public layout")

    root_files: list[tuple[str, FileSnapshot]] = []
    for name in REQUIRED_ROOT_FILES:
        path = require_exact_name(name)
        root_files.append((name, real_file_snapshot(path)))
    for name in ("tests", "scripts"):
        path = require_exact_name(name)
        directory_guards.append((path, real_directory_identity(path)))
    root_file_map = dict(root_files)
    try:
        version = guarded_read_bytes(
            source / "VERSION", root_file_map["VERSION"]
        ).decode(encoding="utf-8", errors="strict").strip()
    except (OSError, UnicodeError) as exc:
        raise ExportError(f"cannot read VERSION as UTF-8: {exc}") from exc
    if SEMVER_RE.fullmatch(version) is None:
        raise ExportError(f"source VERSION is not strict semver: {version!r}")
    if expected_version is not None and version != expected_version:
        raise ExportError(
            f"source VERSION {version!r} does not match --expected-version "
            f"{expected_version!r}"
        )
    try:
        license_text = guarded_read_bytes(
            source / "LICENSE", root_file_map["LICENSE"]
        ).decode(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise ExportError(f"cannot read LICENSE as UTF-8: {exc}") from exc
    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        raise ExportError("source LICENSE is not the declared Apache-2.0 text")
    return SourceValidation(
        version=version,
        root_identity=root_identity,
        directory_guards=tuple(directory_guards),
        root_files=tuple(root_files),
    )


def validate_target(
    source: Path,
    source_identity: PathIdentity,
    target: Path,
    plugin_name: str,
) -> PathIdentity:
    if target.name != plugin_name:
        raise ExportError(
            "output directory name must exactly match --plugin-name "
            f"({plugin_name!r})"
        )
    if target == source or target.is_relative_to(source):
        raise ExportError("output must be outside the source tree")
    reject_linked_directory_components(target.parent)
    parent_identity = real_directory_identity(target.parent)
    current = Path(target.parent.anchor)
    for part in target.parent.parts[1:]:
        current = current / part
        if real_directory_identity(current) == source_identity:
            raise ExportError(
                "output physically aliases the source tree through an ancestor"
            )
    if path_exists_no_follow(target):
        raise ExportError(
            "output already exists; not empty or empty paths are never overwritten"
        )
    return parent_identity


def build_copy_plan(
    source: Path,
    validation: SourceValidation,
) -> list[CopyItem]:
    verify_directory_identity(source, validation.root_identity)
    root_file_map = dict(validation.root_files)
    plan: list[CopyItem] = []
    for name in REQUIRED_ROOT_FILES:
        plan.append(CopyItem(source / name, Path(name), root_file_map[name]))
    for name in OPTIONAL_PUBLIC_ROOT_FILES:
        path = source / name
        if path_exists_no_follow(path):
            plan.append(CopyItem(path, Path(name), real_file_snapshot(path)))
    for skill in EXPECTED_SKILLS:
        skill_root = source / skill
        for path, snapshot in collect_tree_files(skill_root):
            plan.append(
                CopyItem(
                    path,
                    Path("skills") / skill / path.relative_to(skill_root),
                    snapshot,
                )
            )
    for directory_name in ("tests", "scripts"):
        directory = source / directory_name
        for path, snapshot in collect_tree_files(directory):
            plan.append(
                CopyItem(
                    path,
                    Path(directory_name) / path.relative_to(directory),
                    snapshot,
                )
            )
    destinations = [item.destination.as_posix() for item in plan]
    folded_destinations = [path.casefold() for path in destinations]
    if len(folded_destinations) != len(set(folded_destinations)):
        raise ExportError("copy plan contains duplicate destinations")
    forbidden = [
        path
        for path in destinations
        if "plugin_release" in path.casefold()
        or ".git" in {part.casefold() for part in Path(path).parts}
    ]
    if forbidden:
        raise ExportError(f"copy plan contains internal files: {forbidden}")
    for path, identity in validation.directory_guards:
        verify_directory_identity(path, identity)
    verify_directory_identity(source, validation.root_identity)
    return sorted(plan, key=lambda item: item.destination.as_posix())


def public_readme(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ExportError("README.md must be valid UTF-8") from exc
    old = "See [PLUGIN_RELEASE.md](PLUGIN_RELEASE.md)."
    replacement = (
        "The distributable Plugin manifest is stored in "
        ".codex-plugin/plugin.json."
    )
    text = text.replace(old, replacement)
    if "PLUGIN_RELEASE" in text:
        raise ExportError("README.md still exposes the internal Plugin release plan")
    return text.encode("utf-8")


def ensure_candidate_directory(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise ExportError(f"unsafe candidate directory path: {relative}")
    current = root
    for part in relative.parts:
        current = current / part
        try:
            os.mkdir(current, PRIVATE_DIRECTORY_MODE)
        except FileExistsError:
            real_directory_identity(current)
        except OSError as exc:
            raise ExportError(f"cannot create candidate directory {current}: {exc}") from exc
        else:
            real_directory_identity(current)
    return current


def write_candidate_file(root: Path, relative: Path, data: bytes) -> FileSnapshot:
    if (
        relative.is_absolute()
        or not relative.parts
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ExportError(f"unsafe candidate file path: {relative}")
    root_identity = real_directory_identity(root)
    ensure_candidate_directory(root, relative.parent)
    snapshot = exclusive_create_file(root / relative, data)
    verify_directory_identity(root, root_identity)
    return snapshot


def write_candidate_record(root: Path, relative: Path, data: bytes) -> AssembledFile:
    snapshot = write_candidate_file(root, relative, data)
    return AssembledFile(
        relative=relative.as_posix(),
        snapshot=snapshot,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def write_candidate_json(
    root: Path,
    relative: Path,
    payload: dict[str, object],
) -> AssembledFile:
    data = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    return write_candidate_record(root, relative, data)


def candidate_regular_files(root: Path) -> list[tuple[Path, FileSnapshot]]:
    files: list[tuple[Path, FileSnapshot]] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(
                os.scandir(directory),
                key=lambda item: (item.name.casefold(), item.name),
            )
        except OSError as exc:
            raise ExportError(f"cannot inspect candidate directory {directory}: {exc}") from exc
        folded_names: set[str] = set()
        for entry in entries:
            folded = entry.name.casefold()
            if folded in folded_names:
                raise ExportError(
                    f"case-insensitive collision in candidate: {Path(entry.path).relative_to(root)}"
                )
            folded_names.add(folded)
            path = Path(entry.path)
            try:
                result = os.lstat(path)
            except OSError as exc:
                raise ExportError(f"cannot inspect candidate entry {path}: {exc}") from exc
            if stat.S_ISDIR(result.st_mode):
                _identity_from_stat(result, path, "directory")
                visit(path)
            elif stat.S_ISREG(result.st_mode):
                files.append(
                    (
                        path,
                        FileSnapshot(
                            identity=_identity_from_stat(result, path, "file"),
                            size=int(result.st_size),
                            mtime_ns=int(result.st_mtime_ns),
                        ),
                    )
                )
            else:
                _identity_from_stat(result, path, "file")
                raise ExportError(f"unsupported candidate entry: {path.relative_to(root)}")

    real_directory_identity(root)
    visit(root)
    return sorted(files, key=lambda item: item[0].relative_to(root).as_posix())


def verify_assembly_plan(root: Path, plan: AssemblyPlan) -> None:
    """Verify exact bytes against the immutable plan created at write time."""

    verify_directory_identity(root, plan.root_identity)
    expected = {record.relative: record for record in plan.files}
    if len(expected) != len(plan.files):
        raise ExportError("assembly plan contains duplicate paths")
    current_files = candidate_regular_files(root)
    current = {
        path.relative_to(root).as_posix(): (path, snapshot)
        for path, snapshot in current_files
    }
    if set(current) != set(expected):
        missing = sorted(set(expected) - set(current))
        extra = sorted(set(current) - set(expected))
        raise ExportError(
            f"candidate diverged from assembly plan: missing={missing}, extra={extra}"
        )
    for relative, record in expected.items():
        path, snapshot = current[relative]
        if snapshot != record.snapshot:
            raise ExportError(
                f"candidate file snapshot changed after assembly: {relative}"
            )
        digest = hashlib.sha256(
            guarded_read_bytes(path, record.snapshot)
        ).hexdigest()
        if digest != record.sha256:
            raise ExportError(
                f"candidate bytes changed after assembly: {relative}"
            )
    verify_directory_identity(root, plan.root_identity)


def create_staging(target: Path, parent_identity: PathIdentity) -> StagingOwnership:
    verify_directory_identity(target.parent, parent_identity)
    for _attempt in range(32):
        token = secrets.token_hex(16)
        staging = target.parent / f".{target.name}.staging-{token}"
        marker = target.parent / f".{target.name}.owner-{token}"
        try:
            os.mkdir(staging, PRIVATE_DIRECTORY_MODE)
        except FileExistsError:
            continue
        except OSError as exc:
            raise ExportError(f"cannot exclusively create staging directory: {exc}") from exc
        staging_identity = real_directory_identity(staging)
        try:
            marker_snapshot = exclusive_create_file(
                marker,
                f"release-export-owner-v1:{token}\n".encode("ascii"),
            )
        except Exception:
            try:
                if real_directory_identity(staging) == staging_identity:
                    os.rmdir(staging)
            except OSError:
                pass
            raise
        verify_directory_identity(target.parent, parent_identity)
        return StagingOwnership(
            staging=staging,
            staging_identity=staging_identity,
            marker=marker,
            marker_snapshot=marker_snapshot,
            token=token,
            parent=target.parent,
            parent_identity=parent_identity,
        )
    raise ExportError("could not allocate a unique sibling staging directory")


def ownership_marker_is_current(ownership: StagingOwnership) -> bool:
    try:
        if real_file_snapshot(ownership.marker) != ownership.marker_snapshot:
            return False
        content = guarded_read_bytes(ownership.marker, ownership.marker_snapshot)
    except (ExportError, OSError):
        return False
    return content == f"release-export-owner-v1:{ownership.token}\n".encode("ascii")


def remove_current_ownership_marker(ownership: StagingOwnership) -> None:
    if not ownership_marker_is_current(ownership):
        raise ExportError("staging ownership marker changed during export")
    try:
        os.unlink(ownership.marker)
    except OSError as exc:
        raise ExportError(f"cannot remove staging ownership marker: {exc}") from exc


def cleanup_owned_staging(ownership: StagingOwnership) -> None:
    """Remove only owned staging; report every residual instead of guessing."""

    staging_exists = path_exists_no_follow(ownership.staging)
    marker_exists = path_exists_no_follow(ownership.marker)
    if not staging_exists:
        if marker_exists and not ownership_marker_is_current(ownership):
            raise ExportError(
                "cleanup refused a changed ownership marker; residual "
                f"marker={ownership.marker}"
            )
        if marker_exists:
            try:
                os.unlink(ownership.marker)
            except OSError as exc:
                raise ExportError(
                    "cleanup could not remove ownership marker; residual "
                    f"marker={ownership.marker}: {exc}"
                ) from exc
        return

    try:
        current_identity = real_directory_identity(ownership.staging)
    except ExportError as exc:
        raise ExportError(
            "cleanup refused an uninspectable staging object; residual "
            f"staging={ownership.staging}, marker={ownership.marker}: {exc}"
        ) from exc
    if current_identity != ownership.staging_identity:
        raise ExportError(
            "cleanup refused a replaced staging identity; residual "
            f"staging={ownership.staging}, marker={ownership.marker}"
        )
    if not ownership_marker_is_current(ownership):
        raise ExportError(
            "cleanup refused a missing or changed ownership marker; residual "
            f"staging={ownership.staging}, marker={ownership.marker}"
        )
    try:
        shutil.rmtree(ownership.staging)
    except OSError as exc:
        raise ExportError(
            "cleanup could not remove owned staging; residual "
            f"staging={ownership.staging}, marker={ownership.marker}: {exc}"
        ) from exc
    if path_exists_no_follow(ownership.staging):
        raise ExportError(
            "cleanup returned with a residual staging path; residual "
            f"staging={ownership.staging}, marker={ownership.marker}"
        )
    if not ownership_marker_is_current(ownership):
        marker_state = "present but changed" if path_exists_no_follow(
            ownership.marker
        ) else "missing"
        raise ExportError(
            "cleanup could not verify the ownership marker after staging removal; "
            f"marker={ownership.marker} ({marker_state})"
        )
    try:
        os.unlink(ownership.marker)
    except OSError as exc:
        raise ExportError(
            "cleanup removed staging but left the ownership marker; residual "
            f"marker={ownership.marker}: {exc}"
        ) from exc


def atomic_publish_no_replace(staging: Path, target: Path) -> None:
    """Atomically rename a directory while refusing an existing destination."""

    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        move_file_ex = kernel32.MoveFileExW
        move_file_ex.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        move_file_ex.restype = ctypes.c_int
        if not move_file_ex(str(staging), str(target), 0):
            error_code = ctypes.get_last_error()
            message = ctypes.FormatError(error_code)
            if error_code in {80, 183}:
                raise FileExistsError(error_code, message, str(target))
            raise OSError(error_code, message, str(target))
        return

    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise ExportError("this platform cannot guarantee atomic no-replace publication")
        renameat2.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100,
            os.fsencode(staging),
            -100,
            os.fsencode(target),
            1,
        )
        if result != 0:
            error_code = ctypes.get_errno()
            if error_code in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(error_code, os.strerror(error_code), str(target))
            if error_code in {errno.ENOSYS, errno.EINVAL, errno.ENOTSUP}:
                raise ExportError(
                    "filesystem cannot guarantee atomic no-replace publication"
                )
            raise OSError(error_code, os.strerror(error_code), str(target))
        return

    raise ExportError("this platform cannot guarantee atomic no-replace publication")


def verify_source_unchanged(source: Path, validation: SourceValidation) -> None:
    verify_directory_identity(source, validation.root_identity)
    for path, identity in validation.directory_guards:
        verify_directory_identity(path, identity)
    for name, snapshot in validation.root_files:
        if real_file_snapshot(source / name) != snapshot:
            raise ExportError(f"required source file changed during export: {name}")


def assemble_candidate(
    staging: Path,
    plan: list[CopyItem],
    plugin_manifest: dict[str, object],
    release_manifest: dict[str, object],
) -> AssemblyPlan:
    staging_identity = real_directory_identity(staging)
    assembled: list[AssembledFile] = []
    for item in plan:
        data = guarded_read_bytes(item.source, item.snapshot)
        if item.destination.as_posix() == "README.md":
            data = public_readme(data)
        assembled.append(write_candidate_record(staging, item.destination, data))

    assembled.append(
        write_candidate_json(
            staging,
            Path(".codex-plugin") / "plugin.json",
            plugin_manifest,
        )
    )
    release_payload = dict(release_manifest)
    release_payload["inventory"] = {
        "algorithm": "SHA-256",
        "path": "SHA256SUMS",
        "scope": "all regular files except SHA256SUMS",
        "assurance": (
            "package-local consistency only; not publisher identity, provenance, "
            "or release trust"
        ),
        "file_count": len(assembled) + 1,
    }
    assembled.append(
        write_candidate_json(
            staging,
            Path("RELEASE_MANIFEST.json"),
            release_payload,
        )
    )

    before_checksums = AssemblyPlan(
        root_identity=staging_identity,
        files=tuple(sorted(assembled, key=lambda record: record.relative)),
    )
    verify_assembly_plan(staging, before_checksums)

    checksum_data = (
        "\n".join(
            f"{record.sha256}  {record.relative}"
            for record in before_checksums.files
        )
        + "\n"
    ).encode("utf-8")
    assembled.append(
        write_candidate_record(staging, Path("SHA256SUMS"), checksum_data)
    )
    completed = AssemblyPlan(
        root_identity=staging_identity,
        files=tuple(sorted(assembled, key=lambda record: record.relative)),
    )
    verify_assembly_plan(staging, completed)
    return completed


def validate_candidate(
    root: Path,
    *,
    plugin_name: str,
    version: str,
    expected_identity: PathIdentity,
    assembly_plan: AssemblyPlan,
) -> None:
    verify_directory_identity(root, expected_identity)
    if assembly_plan.root_identity != expected_identity:
        raise ExportError("assembly plan is not bound to the candidate directory")
    verify_assembly_plan(root, assembly_plan)
    file_records = candidate_regular_files(root)
    records_by_relative = {
        path.relative_to(root).as_posix(): (path, snapshot)
        for path, snapshot in file_records
    }
    folded_paths = {relative.casefold() for relative in records_by_relative}
    if len(folded_paths) != len(records_by_relative):
        raise ExportError("candidate contains case-insensitive duplicate paths")
    forbidden = [
        relative
        for relative in records_by_relative
        if "plugin_release" in relative.casefold()
        or ".git" in {part.casefold() for part in Path(relative).parts}
        or ".staging-" in relative.casefold()
        or ".owner-" in relative.casefold()
    ]
    if forbidden:
        raise ExportError(f"candidate contains internal or temporary paths: {forbidden}")

    exported_skills = {
        parts[1]
        for relative in records_by_relative
        for parts in [Path(relative).parts]
        if len(parts) == 3 and parts[0] == "skills" and parts[2] == "SKILL.md"
    }
    if exported_skills != set(EXPECTED_SKILLS):
        raise ExportError("exported Skill set changed during assembly")

    required_candidate_files = {
        *REQUIRED_ROOT_FILES,
        ".codex-plugin/plugin.json",
        "RELEASE_MANIFEST.json",
        "SHA256SUMS",
    }
    missing = required_candidate_files - set(records_by_relative)
    if missing:
        raise ExportError(f"candidate is missing required files: {sorted(missing)}")

    plugin_path, plugin_snapshot = records_by_relative[".codex-plugin/plugin.json"]
    plugin = json.loads(
        guarded_read_bytes(plugin_path, plugin_snapshot).decode("utf-8", errors="strict")
    )
    if plugin.get("name") != plugin_name or plugin.get("version") != version:
        raise ExportError("Plugin manifest identity does not match the export contract")

    release_path, release_snapshot = records_by_relative["RELEASE_MANIFEST.json"]
    release = json.loads(
        guarded_read_bytes(release_path, release_snapshot).decode("utf-8", errors="strict")
    )
    inventory = release.get("inventory")
    if not isinstance(inventory, dict) or inventory.get("file_count") != len(file_records) - 1:
        raise ExportError("release inventory file count is not exact")

    checksums_path, checksums_snapshot = records_by_relative["SHA256SUMS"]
    checksum_text = guarded_read_bytes(checksums_path, checksums_snapshot).decode(
        "utf-8", errors="strict"
    )
    declared: dict[str, str] = {}
    for line in checksum_text.splitlines():
        if "  " not in line:
            raise ExportError("SHA256SUMS contains a malformed line")
        digest, relative = line.split("  ", 1)
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None or not relative:
            raise ExportError("SHA256SUMS contains a malformed entry")
        if relative.casefold() in {item.casefold() for item in declared}:
            raise ExportError("SHA256SUMS contains a duplicate path")
        declared[relative] = digest
    expected_checksum_paths = set(records_by_relative) - {"SHA256SUMS"}
    if set(declared) != expected_checksum_paths:
        raise ExportError("SHA256SUMS inventory does not match candidate files")
    for relative, expected_digest in declared.items():
        path, snapshot = records_by_relative[relative]
        actual_digest = hashlib.sha256(guarded_read_bytes(path, snapshot)).hexdigest()
        if actual_digest != expected_digest:
            raise ExportError(f"SHA256SUMS digest mismatch: {relative}")
    verify_assembly_plan(root, assembly_plan)
    verify_directory_identity(root, expected_identity)


def export(args: argparse.Namespace) -> Path:
    source = lexical_absolute(args.source)
    target = lexical_absolute(args.output)
    plugin_name = require_real_text("plugin name", args.plugin_name)
    if PLUGIN_NAME_RE.fullmatch(plugin_name) is None or len(plugin_name) > 64:
        raise ExportError("plugin name must be lower-case hyphen-case and at most 64 characters")
    author_name = require_real_text("author name", args.author_name)
    author_url = require_https_url("author URL", args.author_url)
    repository_url = require_https_url("repository URL", args.repository_url)
    homepage_url = require_https_url("homepage URL", args.homepage_url)
    support_url = require_https_url("support URL", args.support_url)
    privacy_policy_url = require_https_url(
        "privacy policy URL", args.privacy_policy_url
    )
    terms_of_service_url = require_https_url(
        "terms of service URL", args.terms_of_service_url
    )
    description = require_real_text("description", args.description)
    display_name = require_real_text("display name", args.display_name)
    category = require_real_text("category", args.category)
    license_id = require_real_text("license", args.license)
    if license_id != "Apache-2.0":
        raise ExportError(
            "the current source LICENSE is Apache-2.0; --license must match it"
        )
    keywords = tuple(
        dict.fromkeys(
            require_real_text("keyword", keyword)
            for keyword in (args.keyword or DEFAULT_KEYWORDS)
        )
    )
    validation = validate_source(source, args.expected_version)
    version = validation.version
    parent_identity = validate_target(
        source,
        validation.root_identity,
        target,
        plugin_name,
    )
    plan = build_copy_plan(source, validation)

    plugin_manifest: dict[str, object] = {
        "name": plugin_name,
        "version": version,
        "description": description,
        "author": {
            "name": author_name,
            "url": author_url,
        },
        "homepage": homepage_url,
        "repository": repository_url,
        "license": license_id,
        "keywords": list(keywords),
        "skills": "./skills/",
        "interface": {
            "displayName": display_name,
            "shortDescription": description,
            "longDescription": description,
            "developerName": author_name,
            "category": category,
            "capabilities": [
                "Research",
                "Writing",
                "Workflow",
            ],
            "websiteURL": homepage_url,
            "privacyPolicyURL": privacy_policy_url,
            "termsOfServiceURL": terms_of_service_url,
            "defaultPrompt": [
                "Organize a durable research workspace.",
                "Audit a literature review with traceable evidence.",
                "Deliver a reproducible research artifact.",
            ],
        },
    }
    release_manifest: dict[str, object] = {
        "schema_version": 1,
        "plugin_name": plugin_name,
        "version": version,
        "license": license_id,
        "publisher": {
            "name": author_name,
            "url": author_url,
        },
        "repository_url": repository_url,
        "homepage_url": homepage_url,
        "support_url": support_url,
        "privacy_policy_url": privacy_policy_url,
        "terms_of_service_url": terms_of_service_url,
        "source_layout": "flat-suite-source",
        "export_layout": "public-root-with-skills",
        "skills": list(EXPECTED_SKILLS),
    }

    ownership = create_staging(target, parent_identity)
    try:
        assembly_plan = assemble_candidate(
            ownership.staging,
            plan,
            plugin_manifest,
            release_manifest,
        )
        verify_source_unchanged(source, validation)
        verify_directory_identity(ownership.parent, ownership.parent_identity)
        verify_directory_identity(ownership.staging, ownership.staging_identity)
        if not ownership_marker_is_current(ownership):
            raise ExportError("staging ownership marker changed before acceptance")
        validate_candidate(
            ownership.staging,
            plugin_name=plugin_name,
            version=version,
            expected_identity=ownership.staging_identity,
            assembly_plan=assembly_plan,
        )
        verify_directory_identity(ownership.parent, ownership.parent_identity)
        if path_exists_no_follow(target):
            raise ExportError("output appeared concurrently; refusing to overwrite it")
        try:
            atomic_publish_no_replace(ownership.staging, target)
        except FileExistsError as exc:
            raise ExportError(
                "output appeared concurrently; atomic publication refused replacement"
            ) from exc
        published_identity = real_directory_identity(target)
        if published_identity != ownership.staging_identity:
            raise ExportError("output was replaced during atomic publication")
        verify_directory_identity(ownership.parent, ownership.parent_identity)
        validate_candidate(
            target,
            plugin_name=plugin_name,
            version=version,
            expected_identity=ownership.staging_identity,
            assembly_plan=assembly_plan,
        )
        remove_current_ownership_marker(ownership)
        verify_directory_identity(target, ownership.staging_identity)
        verify_directory_identity(ownership.parent, ownership.parent_identity)
        return target
    except Exception as primary:
        try:
            cleanup_owned_staging(ownership)
        except ExportError as cleanup_error:
            raise ExportError(
                f"{primary}; cleanup failed: {cleanup_error}"
            ) from primary
        raise


def main() -> int:
    configure_utf8_streams()
    args = parse_args()
    try:
        target = export(args)
    except (ExportError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"EXPORTED: {target}")
    print("RESULT: EXPORT COMPLETE (release checks still required)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
