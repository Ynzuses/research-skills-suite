#!/usr/bin/env python3
"""Safely apply an approved workspace-memory bootstrap manifest.

The helper is deliberately mechanical.  It never infers a directory design,
changes an existing control-plane file, replaces an instruction entry, moves
or deletes assets, invokes another process, or performs network operations.
"""

from __future__ import annotations

import argparse
import copy
import ctypes
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Sequence


SCHEMA_VERSION = 1
MANAGED_BLOCK_ID = "manage-workspace-memory-v1"
START_MARKER = "<!-- manage-workspace-memory:managed-block:start -->"
END_MARKER = "<!-- manage-workspace-memory:managed-block:end -->"
MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown"}
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_CONTENT_BYTES = 1024 * 1024
MAX_TOTAL_CONTENT_BYTES = 4 * 1024 * 1024
SHA256_RE = re.compile(r"[0-9a-f]{64}")
DECISION_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{1,199}")
ALLOWED_ROLES = {
    "workspace_rules",
    "long_term_memory",
    "current_status",
    "stable_design",
    "asset_index",
    "dependency_graph",
    "history",
    "topic_memory",
    "workspace_blueprint",
    "audit_index",
}
FORBIDDEN_PATH_PARTS = {
    ".git",
    ".hg",
    ".svn",
    ".nox",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "hooks",
    "node_modules",
    "scheduled-tasks",
    "venv",
    "workflows",
}
WINDOWS_RESERVED_NAMES = {
    "aux",
    "con",
    "nul",
    "prn",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


class ManifestError(RuntimeError):
    """The manifest is malformed, incomplete, or not approved."""


class BootstrapConflict(RuntimeError):
    """The approved plan conflicts with current workspace state."""


class ApplyError(RuntimeError):
    """The filesystem changed after preflight or an approved write failed."""


@dataclass(frozen=True)
class FileSpec:
    path: str
    role: str
    content: bytes
    content_sha256: str


@dataclass(frozen=True)
class EntrySpec:
    path: str
    create_if_missing: bool
    operation: str
    previous_managed_block_sha256: str | None
    content: str
    content_sha256: str


@dataclass(frozen=True)
class ApprovedManifest:
    decision_id: str
    approved_by_role: str
    approved_at: str
    approved_manifest_sha256: str
    root_identity: "RootIdentity"
    frozen_paths: tuple[str, ...]
    directories: tuple[str, ...]
    files: tuple[FileSpec, ...]
    entry: EntrySpec


@dataclass(frozen=True)
class PathIdentity:
    device: int
    inode: int
    mode: int

    def public(self) -> dict[str, int]:
        return {
            "device": self.device,
            "inode": self.inode,
            "mode": self.mode,
        }


@dataclass(frozen=True)
class RootIdentity:
    normalized_path_sha256: str
    device: int
    inode: int

    def public(self) -> dict[str, int | str]:
        return {
            "normalized_path_sha256": self.normalized_path_sha256,
            "device": self.device,
            "inode": self.inode,
        }


@dataclass(frozen=True)
class BoundPath:
    relative_path: str
    identity: PathIdentity

    def public(self) -> dict[str, Any]:
        return {
            "path": self.relative_path,
            "identity": self.identity.public(),
        }


@dataclass(frozen=True)
class FileSnapshot:
    identity: PathIdentity
    link_count: int
    size: int
    modified_ns: int
    changed_ns: int
    user_id: int
    group_id: int
    sha256: str

    def public(self) -> dict[str, Any]:
        return {
            "identity": self.identity.public(),
            "link_count": self.link_count,
            "size": self.size,
            "modified_ns": self.modified_ns,
            "changed_ns": self.changed_ns,
            "user_id": self.user_id,
            "group_id": self.group_id,
            "sha256": self.sha256,
        }


@dataclass
class PlannedChange:
    kind: str
    relative_path: str
    state: str
    pre_sha256: str | None = None
    planned_post_sha256: str | None = None
    observed_post_sha256: str | None = None
    target: Path | None = None
    payload: bytes | None = None
    target_identity: PathIdentity | None = None
    pre_snapshot: FileSnapshot | None = None
    parent_chain: tuple[BoundPath, ...] = ()

    def public(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "path": self.relative_path,
            "state": self.state,
            "pre_sha256": self.pre_sha256,
            "planned_post_sha256": self.planned_post_sha256,
            "observed_post_sha256": self.observed_post_sha256,
            "pre_snapshot": (self.pre_snapshot.public() if self.pre_snapshot is not None else None),
            "target_identity": (
                self.target_identity.public() if self.target_identity is not None else None
            ),
            "bound_parent_chain": [item.public() for item in self.parent_chain],
        }


@dataclass(frozen=True)
class RecoveryItem:
    relative_path: str
    kind: str
    action: str
    actual_path: str | None = None
    identity: PathIdentity | None = None
    sha256: str | None = None

    def public(self) -> dict[str, Any]:
        return {
            "path": self.relative_path,
            "kind": self.kind,
            "action": self.action,
            "actual_path": self.actual_path,
            "identity": self.identity.public() if self.identity is not None else None,
            "sha256": self.sha256,
        }


def configure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def require_object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ManifestError(f"{context} must be an object")
    return value


def require_exact_keys(value: dict[str, Any], required: set[str], context: str) -> None:
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    if missing:
        raise ManifestError(f"{context} is missing keys: {missing}")
    if unknown:
        raise ManifestError(f"{context} has unsupported keys: {unknown}")


def require_string(value: Any, context: str, *, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ManifestError(f"{context} must be a non-empty string of at most {maximum} characters")
    if any(ord(character) < 32 and character not in "\n\r\t" for character in value):
        raise ManifestError(f"{context} contains a control character")
    return value


def duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def reject_json_constant(value: str) -> None:
    raise ManifestError(f"non-finite JSON number is not supported: {value}")


def load_json_manifest(path: Path) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ManifestError(f"cannot inspect manifest {path}: {exc}") from exc
    if size > MAX_MANIFEST_BYTES:
        raise ManifestError(f"manifest exceeds {MAX_MANIFEST_BYTES} bytes: {size}")
    try:
        text = path.read_text(encoding="utf-8-sig", errors="strict")
    except (OSError, UnicodeError) as exc:
        raise ManifestError(f"cannot read strict UTF-8 manifest {path}: {exc}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=duplicate_rejecting_object,
            parse_constant=reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise ManifestError(
            f"invalid JSON manifest at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    return require_object(value, "manifest")


def canonical_manifest_sha256(value: dict[str, Any]) -> str:
    canonical = copy.deepcopy(value)
    approval = require_object(canonical.get("approval"), "approval")
    if "manifest_sha256" not in approval:
        raise ManifestError("approval is missing key: 'manifest_sha256'")
    approval["manifest_sha256"] = None
    try:
        payload = json.dumps(
            canonical,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ManifestError(f"cannot canonicalize manifest for approval: {exc}") from exc
    return sha256_bytes(payload)


def validate_approval_time(value: Any) -> str:
    approved_at = require_string(value, "approval.approved_at", maximum=100)
    try:
        parsed = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManifestError("approval.approved_at must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ManifestError("approval.approved_at must include a time-zone offset")
    return approved_at


def validate_relative_path(value: Any, context: str) -> str:
    path_text = require_string(value, context)
    if path_text != path_text.strip():
        raise ManifestError(f"{context} has leading or trailing whitespace")
    if "\\" in path_text:
        raise ManifestError(f"{context} must use forward slashes")
    if path_text.startswith(("/", "~")) or re.match(r"^[A-Za-z]:", path_text):
        raise ManifestError(f"{context} must be repository-relative")
    pure = PurePosixPath(path_text)
    if pure.is_absolute() or not pure.parts or pure == PurePosixPath("."):
        raise ManifestError(f"{context} cannot name the workspace root")
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise ManifestError(f"{context} contains dot or parent traversal")
    for part in pure.parts:
        if part.endswith((" ", ".")) or ":" in part:
            raise ManifestError(f"{context} is not portable: {path_text!r}")
        base_name = part.split(".", 1)[0].casefold()
        if base_name in WINDOWS_RESERVED_NAMES:
            raise ManifestError(f"{context} uses a reserved path name: {part!r}")
        if part.casefold() in FORBIDDEN_PATH_PARTS:
            raise ManifestError(
                f"{context} targets a forbidden automation or internal path: {part!r}"
            )
    return pure.as_posix()


def require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ManifestError(f"{context} must be an array")
    return value


def validate_sha256(value: Any, context: str) -> str:
    digest = require_string(value, context, maximum=64)
    if SHA256_RE.fullmatch(digest) is None:
        raise ManifestError(f"{context} must be a lowercase SHA-256 digest")
    return digest


def validate_markdown_target(path_text: str, context: str) -> None:
    if PurePosixPath(path_text).suffix.casefold() not in MARKDOWN_SUFFIXES:
        raise ManifestError(f"{context} must target a Markdown file")


def parse_manifest(value: dict[str, Any]) -> ApprovedManifest:
    top_keys = {
        "schema_version",
        "approval",
        "workspace",
        "directories",
        "files",
        "entry",
    }
    require_exact_keys(value, top_keys, "manifest")
    if type(value["schema_version"]) is not int or value["schema_version"] != SCHEMA_VERSION:
        raise ManifestError(f"schema_version must be the integer {SCHEMA_VERSION}")

    approval = require_object(value["approval"], "approval")
    approval_keys = {
        "state",
        "decision_id",
        "approved_by_role",
        "approved_at",
        "manifest_sha256",
    }
    require_exact_keys(approval, approval_keys, "approval")
    if approval["state"] != "approved":
        raise ManifestError("manifest approval.state is not 'approved'")
    decision_id = require_string(approval["decision_id"], "approval.decision_id", maximum=200)
    if DECISION_ID_RE.fullmatch(decision_id) is None:
        raise ManifestError("approval.decision_id is not a stable portable identifier")
    approved_by_role = require_string(
        approval["approved_by_role"], "approval.approved_by_role", maximum=200
    )
    approved_at = validate_approval_time(approval["approved_at"])
    approved_manifest_sha256 = validate_sha256(
        approval["manifest_sha256"], "approval.manifest_sha256"
    )
    observed_manifest_sha256 = canonical_manifest_sha256(value)
    if approved_manifest_sha256 != observed_manifest_sha256:
        raise ManifestError(
            "approval.manifest_sha256 does not match the canonical complete manifest"
        )

    workspace = require_object(value["workspace"], "workspace")
    workspace_keys = {
        "root",
        "root_identity",
        "frozen_inventory_complete",
        "frozen_paths",
    }
    require_exact_keys(workspace, workspace_keys, "workspace")
    if workspace["root"] != ".":
        raise ManifestError("workspace.root must be '.'")
    root_identity_value = require_object(workspace["root_identity"], "workspace.root_identity")
    require_exact_keys(
        root_identity_value,
        {"normalized_path_sha256", "device", "inode"},
        "workspace.root_identity",
    )
    normalized_path_sha256 = validate_sha256(
        root_identity_value["normalized_path_sha256"],
        "workspace.root_identity.normalized_path_sha256",
    )
    for field in ("device", "inode"):
        if type(root_identity_value[field]) is not int or root_identity_value[field] < 0:
            raise ManifestError(f"workspace.root_identity.{field} must be a non-negative integer")
    root_identity = RootIdentity(
        normalized_path_sha256=normalized_path_sha256,
        device=root_identity_value["device"],
        inode=root_identity_value["inode"],
    )
    if workspace["frozen_inventory_complete"] is not True:
        raise ManifestError("workspace.frozen_inventory_complete must be true before approval")
    frozen_paths = tuple(
        validate_relative_path(item, f"workspace.frozen_paths[{index}]")
        for index, item in enumerate(
            require_list(workspace["frozen_paths"], "workspace.frozen_paths")
        )
    )

    directories = tuple(
        validate_relative_path(item, f"directories[{index}]")
        for index, item in enumerate(require_list(value["directories"], "directories"))
    )

    files: list[FileSpec] = []
    total_content_bytes = 0
    for index, raw_file in enumerate(require_list(value["files"], "files")):
        context = f"files[{index}]"
        file_value = require_object(raw_file, context)
        file_keys = {"path", "role", "content", "content_sha256"}
        require_exact_keys(file_value, file_keys, context)
        path_text = validate_relative_path(file_value["path"], f"{context}.path")
        validate_markdown_target(path_text, f"{context}.path")
        role = require_string(file_value["role"], f"{context}.role", maximum=100)
        if role not in ALLOWED_ROLES:
            raise ManifestError(f"{context}.role is unsupported: {role!r}")
        content_text = require_string(
            file_value["content"], f"{context}.content", maximum=MAX_CONTENT_BYTES
        )
        content = content_text.encode("utf-8", errors="strict")
        if len(content) > MAX_CONTENT_BYTES:
            raise ManifestError(f"{context}.content exceeds {MAX_CONTENT_BYTES} bytes")
        content_sha256 = validate_sha256(file_value["content_sha256"], f"{context}.content_sha256")
        if sha256_bytes(content) != content_sha256:
            raise ManifestError(f"{context}.content_sha256 does not match content")
        total_content_bytes += len(content)
        files.append(FileSpec(path_text, role, content, content_sha256))

    entry_value = require_object(value["entry"], "entry")
    entry_keys = {
        "path",
        "create_if_missing",
        "operation",
        "previous_managed_block_sha256",
        "managed_block_id",
        "content",
        "content_sha256",
    }
    require_exact_keys(entry_value, entry_keys, "entry")
    entry_path = validate_relative_path(entry_value["path"], "entry.path")
    validate_markdown_target(entry_path, "entry.path")
    if type(entry_value["create_if_missing"]) is not bool:
        raise ManifestError("entry.create_if_missing must be a boolean")
    operation = require_string(entry_value["operation"], "entry.operation", maximum=20)
    if operation not in {"merge", "update"}:
        raise ManifestError("entry.operation must be 'merge' or 'update'")
    previous_block_value = entry_value["previous_managed_block_sha256"]
    if operation == "merge":
        if previous_block_value is not None:
            raise ManifestError(
                "entry.previous_managed_block_sha256 must be null for operation='merge'"
            )
        previous_managed_block_sha256 = None
    else:
        previous_managed_block_sha256 = validate_sha256(
            previous_block_value,
            "entry.previous_managed_block_sha256",
        )
        if entry_value["create_if_missing"]:
            raise ManifestError("entry operation='update' cannot create a missing entry")
    if entry_value["managed_block_id"] != MANAGED_BLOCK_ID:
        raise ManifestError(f"entry.managed_block_id must be {MANAGED_BLOCK_ID!r}")
    entry_content = require_string(
        entry_value["content"], "entry.content", maximum=MAX_CONTENT_BYTES
    )
    if START_MARKER in entry_content or END_MARKER in entry_content:
        raise ManifestError("entry.content must not contain managed-block markers")
    entry_content_bytes = entry_content.encode("utf-8", errors="strict")
    if len(entry_content_bytes) > MAX_CONTENT_BYTES:
        raise ManifestError(f"entry.content exceeds {MAX_CONTENT_BYTES} bytes")
    entry_sha256 = validate_sha256(entry_value["content_sha256"], "entry.content_sha256")
    if sha256_bytes(entry_content_bytes) != entry_sha256:
        raise ManifestError("entry.content_sha256 does not match entry.content")
    total_content_bytes += len(entry_content_bytes)
    if total_content_bytes > MAX_TOTAL_CONTENT_BYTES:
        raise ManifestError(f"rendered content exceeds {MAX_TOTAL_CONTENT_BYTES} total bytes")

    ensure_unique_paths(directories, files, entry_path, frozen_paths)
    return ApprovedManifest(
        decision_id=decision_id,
        approved_by_role=approved_by_role,
        approved_at=approved_at,
        approved_manifest_sha256=approved_manifest_sha256,
        root_identity=root_identity,
        frozen_paths=frozen_paths,
        directories=directories,
        files=tuple(files),
        entry=EntrySpec(
            path=entry_path,
            create_if_missing=entry_value["create_if_missing"],
            operation=operation,
            previous_managed_block_sha256=previous_managed_block_sha256,
            content=entry_content,
            content_sha256=entry_sha256,
        ),
    )


def path_key(path_text: str) -> tuple[str, ...]:
    return tuple(part.casefold() for part in PurePosixPath(path_text).parts)


def is_path_within(path_text: str, parent_text: str) -> bool:
    path_parts = path_key(path_text)
    parent_parts = path_key(parent_text)
    return path_parts[: len(parent_parts)] == parent_parts


def ensure_unique_paths(
    directories: Sequence[str],
    files: Sequence[FileSpec],
    entry_path: str,
    frozen_paths: Sequence[str],
) -> None:
    for label, paths in (
        ("directories", directories),
        ("files", [item.path for item in files]),
        ("workspace.frozen_paths", frozen_paths),
    ):
        keys = [path_key(path) for path in paths]
        if len(keys) != len(set(keys)):
            raise ManifestError(f"{label} contains duplicate portable paths")

    file_paths = [item.path for item in files]
    occupied = file_paths + [entry_path]
    occupied_keys = [path_key(path) for path in occupied]
    if len(occupied_keys) != len(set(occupied_keys)):
        raise ManifestError("files and entry contain a duplicate target")
    directory_keys = {path_key(path) for path in directories}
    overlap = [path for path in occupied if path_key(path) in directory_keys]
    if overlap:
        raise ManifestError(f"file target is also declared as a directory: {overlap}")
    for file_path in occupied:
        for other_path in occupied:
            if file_path == other_path:
                continue
            if is_path_within(other_path, file_path):
                raise ManifestError(
                    f"file target cannot be a parent of another target: {file_path!r}"
                )


def resolve_root(root_argument: Path) -> Path:
    try:
        root = root_argument.expanduser().resolve(strict=True)
    except OSError as exc:
        raise ManifestError(f"cannot resolve workspace root {root_argument}: {exc}") from exc
    if not root.is_dir():
        raise ManifestError(f"workspace root is not a directory: {root}")
    return root


def path_identity(info: os.stat_result) -> PathIdentity:
    return PathIdentity(
        device=int(info.st_dev),
        inode=int(info.st_ino),
        mode=int(info.st_mode),
    )


def has_reparse_or_link_identity(info: os.stat_result) -> bool:
    file_attributes = int(getattr(info, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(info.st_mode) or bool(file_attributes & reparse_flag)


def normalized_root_path(root: Path) -> str:
    normalized = os.path.normcase(os.path.normpath(str(root)))
    return unicodedata.normalize("NFC", normalized.replace("\\", "/"))


def inspect_root_identity(
    root: Path, error_type: type[RuntimeError] = ManifestError
) -> RootIdentity:
    try:
        info = os.stat(root, follow_symlinks=False)
    except OSError as exc:
        raise error_type(f"cannot bind workspace root identity: {exc}") from exc
    if has_reparse_or_link_identity(info) or not stat.S_ISDIR(info.st_mode):
        raise error_type("workspace root must resolve to a non-reparse directory")
    return RootIdentity(
        normalized_path_sha256=sha256_bytes(
            normalized_root_path(root).encode("utf-8", errors="strict")
        ),
        device=int(info.st_dev),
        inode=int(info.st_ino),
    )


def require_approved_root(
    root: Path,
    expected: RootIdentity,
    error_type: type[RuntimeError] = ManifestError,
) -> RootIdentity:
    observed = inspect_root_identity(root, error_type)
    if observed != expected:
        raise error_type(
            "workspace root identity differs from the approved normalized path/device/inode"
        )
    return observed


def is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def target_path(
    root: Path,
    path_text: str,
    error_type: type[RuntimeError] = BootstrapConflict,
) -> Path:
    pure = PurePosixPath(path_text)
    lexical = root.joinpath(*pure.parts)
    current = root
    for part in pure.parts:
        current = current / part
        try:
            exists_lexically = os.path.lexists(current)
            info = os.stat(current, follow_symlinks=False) if exists_lexically else None
        except OSError as exc:
            raise error_type(f"cannot inspect path component {current}: {exc}") from exc
        if info is not None and has_reparse_or_link_identity(info):
            raise error_type(
                f"target uses a symbolic-link, junction, or reparse component: {path_text!r}"
            )
    try:
        resolved = lexical.resolve(strict=False)
    except OSError as exc:
        raise error_type(f"cannot resolve target {path_text!r}: {exc}") from exc
    if not is_within_root(resolved, root):
        raise error_type(f"target escapes workspace root: {path_text!r}")
    return lexical


def workspace_relative(root: Path, path: Path) -> str:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return str(path)
    return "." if relative == Path(".") else relative.as_posix()


def snapshot_parent_chain(
    root: Path,
    target: Path,
    *,
    require_complete: bool,
    error_type: type[RuntimeError],
) -> tuple[BoundPath, ...]:
    try:
        parent = target.parent.relative_to(root)
    except ValueError as exc:
        raise error_type(f"target parent escapes workspace root: {target}") from exc
    chain: list[BoundPath] = []
    current = root
    parent_parts = () if parent == Path(".") else parent.parts
    for relative_path, component in [
        (".", root),
        *[
            (Path(*parent_parts[:index]).as_posix(), root.joinpath(*parent_parts[:index]))
            for index in range(1, len(parent_parts) + 1)
        ],
    ]:
        current = component
        try:
            exists_lexically = os.path.lexists(current)
            if not exists_lexically:
                if require_complete:
                    raise error_type(
                        f"parent chain disappeared before write: {workspace_relative(root, current)!r}"
                    )
                break
            info = os.stat(current, follow_symlinks=False)
        except OSError as exc:
            raise error_type(f"cannot inspect parent chain {current}: {exc}") from exc
        if has_reparse_or_link_identity(info):
            raise error_type(
                f"parent chain contains a symbolic-link, junction, or reparse point: "
                f"{workspace_relative(root, current)!r}"
            )
        if not stat.S_ISDIR(info.st_mode):
            raise error_type(
                f"parent-chain component is not a directory: {workspace_relative(root, current)!r}"
            )
        chain.append(BoundPath(relative_path, path_identity(info)))
    return tuple(chain)


def verify_parent_chain(
    root: Path,
    target: Path,
    expected: Sequence[BoundPath],
    *,
    require_complete: bool,
    error_type: type[RuntimeError],
) -> tuple[BoundPath, ...]:
    observed = snapshot_parent_chain(
        root,
        target,
        require_complete=require_complete,
        error_type=error_type,
    )
    if len(observed) < len(expected) or tuple(observed[: len(expected)]) != tuple(expected):
        raise error_type(
            f"parent-chain identity changed after preflight: "
            f"{workspace_relative(root, target.parent)!r}"
        )
    return observed


def file_snapshot(info: os.stat_result, content: bytes) -> FileSnapshot:
    return FileSnapshot(
        identity=path_identity(info),
        link_count=int(info.st_nlink),
        size=int(info.st_size),
        modified_ns=int(info.st_mtime_ns),
        changed_ns=int(info.st_ctime_ns),
        user_id=int(getattr(info, "st_uid", 0)),
        group_id=int(getattr(info, "st_gid", 0)),
        sha256=sha256_bytes(content),
    )


def require_regular_single_link(
    info: os.stat_result,
    path_text: str,
    error_type: type[RuntimeError],
) -> None:
    if has_reparse_or_link_identity(info) or not stat.S_ISREG(info.st_mode):
        raise error_type(f"target is not a non-reparse regular file: {path_text!r}")
    if int(info.st_nlink) != 1:
        raise error_type(
            f"existing writable target has link count {info.st_nlink}, expected 1: {path_text!r}"
        )


def require_manifest_disjoint(
    root: Path,
    manifest_path: Path,
    manifest: ApprovedManifest,
    error_type: type[RuntimeError] = ManifestError,
) -> PathIdentity:
    """Bind the manifest and reject any target that aliases its physical file."""
    try:
        manifest_info = os.stat(manifest_path, follow_symlinks=False)
    except OSError as exc:
        raise error_type(f"cannot bind approved manifest identity: {exc}") from exc
    require_regular_single_link(manifest_info, str(manifest_path), error_type)
    manifest_identity = path_identity(manifest_info)
    targets = [item.path for item in manifest.files] + [manifest.entry.path]
    for relative_path in targets:
        candidate = root.joinpath(*PurePosixPath(relative_path).parts)
        if not os.path.lexists(candidate):
            continue
        try:
            candidate_info = os.stat(candidate, follow_symlinks=False)
        except OSError as exc:
            raise error_type(
                f"cannot compare manifest with target {relative_path!r}: {exc}"
            ) from exc
        if path_identity(candidate_info) == manifest_identity:
            raise error_type(
                f"approved manifest and target name the same physical file: {relative_path!r}"
            )
    return manifest_identity


def read_bound_file(
    root: Path,
    target: Path,
    path_text: str,
    *,
    expected_snapshot: FileSnapshot | None = None,
    expected_parent_chain: Sequence[BoundPath] = (),
    error_type: type[RuntimeError] = BootstrapConflict,
) -> tuple[bytes, FileSnapshot, tuple[BoundPath, ...]]:
    parent_before = verify_parent_chain(
        root,
        target,
        expected_parent_chain,
        require_complete=True,
        error_type=error_type,
    )
    target_path(root, path_text, error_type)
    try:
        path_before = os.stat(target, follow_symlinks=False)
    except OSError as exc:
        raise error_type(f"cannot bind file before open {path_text!r}: {exc}") from exc
    require_regular_single_link(path_before, path_text, error_type)
    before_identity = path_identity(path_before)
    if expected_snapshot is not None and before_identity != expected_snapshot.identity:
        raise error_type(f"file identity changed after preflight: {path_text!r}")

    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    descriptor: int | None = None
    try:
        descriptor = os.open(target, flags)
        opened_before = os.fstat(descriptor)
        require_regular_single_link(opened_before, path_text, error_type)
        if path_identity(opened_before) != before_identity:
            raise error_type(f"file identity changed while opening: {path_text!r}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        content = b"".join(chunks)
        opened_after = os.fstat(descriptor)
        require_regular_single_link(opened_after, path_text, error_type)
        if path_identity(opened_after) != before_identity:
            raise error_type(f"opened file identity changed during read: {path_text!r}")
    except OSError as exc:
        raise error_type(f"cannot read bound file {path_text!r}: {exc}") from exc
    finally:
        if descriptor is not None:
            os.close(descriptor)

    try:
        path_after = os.stat(target, follow_symlinks=False)
    except OSError as exc:
        raise error_type(f"cannot rebind file after open {path_text!r}: {exc}") from exc
    require_regular_single_link(path_after, path_text, error_type)
    if path_identity(path_after) != before_identity:
        raise error_type(f"file identity changed after open: {path_text!r}")
    parent_after = verify_parent_chain(
        root,
        target,
        parent_before,
        require_complete=True,
        error_type=error_type,
    )
    observed = file_snapshot(path_after, content)
    if expected_snapshot is not None and observed != expected_snapshot:
        raise error_type(f"file state changed after preflight: {path_text!r}")
    return content, observed, parent_after


def ensure_not_frozen(path_text: str, frozen_paths: Sequence[str]) -> None:
    for frozen_path in frozen_paths:
        if is_path_within(path_text, frozen_path):
            raise BootstrapConflict(f"target {path_text!r} is inside frozen path {frozen_path!r}")


def ensure_declared_parent(
    root: Path, path_text: str, declared_directories: set[tuple[str, ...]]
) -> None:
    parent = PurePosixPath(path_text).parent
    if parent == PurePosixPath("."):
        return
    parent_text = parent.as_posix()
    parent_target = target_path(root, parent_text)
    if parent_target.exists():
        if not parent_target.is_dir():
            raise BootstrapConflict(f"parent of {path_text!r} exists but is not a directory")
        return
    if path_key(parent_text) not in declared_directories:
        raise BootstrapConflict(f"missing parent {parent_text!r} is not declared in directories")


def detect_newline(raw: bytes, path_text: str) -> str:
    without_crlf = raw.replace(b"\r\n", b"")
    if b"\r" in without_crlf:
        raise BootstrapConflict(f"entry uses unsupported bare CR newlines: {path_text!r}")
    if b"\r\n" in raw and b"\n" in without_crlf:
        raise BootstrapConflict(f"entry uses mixed LF and CRLF newlines: {path_text!r}")
    return "\r\n" if b"\r\n" in raw else "\n"


def normalized_entry_content(content: str, newline: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return normalized.rstrip("\n").replace("\n", newline)


def managed_block(content: str, newline: str) -> tuple[str, bytes]:
    core = (
        START_MARKER + newline + normalized_entry_content(content, newline) + newline + END_MARKER
    )
    return core, (core + newline).encode("utf-8", errors="strict")


def plan_entry(root: Path, spec: EntrySpec) -> PlannedChange:
    target = target_path(root, spec.path)
    if os.path.lexists(target):
        try:
            raw, snapshot, parent_chain = read_bound_file(
                root,
                target,
                spec.path,
                error_type=BootstrapConflict,
            )
            text = raw.decode("utf-8-sig", errors="strict")
        except UnicodeError as exc:
            raise BootstrapConflict(f"cannot read strict UTF-8 entry {spec.path!r}: {exc}") from exc
        newline = detect_newline(raw, spec.path)
        core, block = managed_block(spec.content, newline)
        start_count = text.count(START_MARKER)
        end_count = text.count(END_MARKER)
        pre_hash = snapshot.sha256
        if start_count == 0 and end_count == 0:
            if spec.operation == "update":
                raise BootstrapConflict(
                    f"entry operation='update' requires an existing managed block: {spec.path!r}"
                )
            newline_bytes = newline.encode("ascii")
            if not raw:
                separator = b""
            elif raw.endswith(newline_bytes * 2):
                separator = b""
            elif raw.endswith(newline_bytes):
                separator = newline_bytes
            else:
                separator = newline_bytes * 2
            post_payload = raw + separator + block
            return PlannedChange(
                kind="entry",
                relative_path=spec.path,
                state="planned_merge",
                pre_sha256=pre_hash,
                planned_post_sha256=sha256_bytes(post_payload),
                target=target,
                payload=post_payload,
                target_identity=snapshot.identity,
                pre_snapshot=snapshot,
                parent_chain=parent_chain,
            )
        if start_count != 1 or end_count != 1:
            raise BootstrapConflict(
                f"entry has partial or repeated managed-block markers: {spec.path!r}"
            )
        start = text.find(START_MARKER)
        end = text.find(END_MARKER, start + len(START_MARKER))
        if end < start:
            raise BootstrapConflict(f"entry managed-block markers are out of order: {spec.path!r}")
        after_end = end + len(END_MARKER)
        if (start > 0 and text[start - 1] not in "\r\n") or (
            after_end < len(text) and text[after_end] not in "\r\n"
        ):
            raise BootstrapConflict(
                f"entry managed-block markers are not standalone lines: {spec.path!r}"
            )
        existing_core = text[start:after_end]
        if existing_core == core:
            return PlannedChange(
                kind="entry",
                relative_path=spec.path,
                state="unchanged",
                pre_sha256=pre_hash,
                planned_post_sha256=pre_hash,
                target=target,
                target_identity=snapshot.identity,
                pre_snapshot=snapshot,
                parent_chain=parent_chain,
            )
        if spec.operation != "update":
            raise BootstrapConflict(
                f"entry managed block differs from the approved manifest: {spec.path!r}"
            )
        start_marker_bytes = START_MARKER.encode("ascii")
        end_marker_bytes = END_MARKER.encode("ascii")
        byte_start = raw.find(start_marker_bytes)
        byte_end_marker = raw.find(end_marker_bytes, byte_start + len(start_marker_bytes))
        if byte_start < 0 or byte_end_marker < 0:
            raise BootstrapConflict(
                f"entry managed block byte boundaries are ambiguous: {spec.path!r}"
            )
        byte_after_end = byte_end_marker + len(end_marker_bytes)
        existing_block = raw[byte_start:byte_after_end]
        existing_block_sha256 = sha256_bytes(existing_block)
        if existing_block_sha256 != spec.previous_managed_block_sha256:
            raise BootstrapConflict(
                f"entry previous managed-block SHA-256 differs from the approved update: "
                f"{spec.path!r}"
            )
        replacement_core = core.encode("utf-8", errors="strict")
        post_payload = raw[:byte_start] + replacement_core + raw[byte_after_end:]
        return PlannedChange(
            kind="entry",
            relative_path=spec.path,
            state="planned_update",
            pre_sha256=pre_hash,
            planned_post_sha256=sha256_bytes(post_payload),
            target=target,
            payload=post_payload,
            target_identity=snapshot.identity,
            pre_snapshot=snapshot,
            parent_chain=parent_chain,
        )

    if not spec.create_if_missing:
        raise BootstrapConflict(f"entry is missing and create_if_missing is false: {spec.path!r}")
    if spec.operation != "merge":
        raise BootstrapConflict(f"entry operation='update' cannot create: {spec.path!r}")
    _, block = managed_block(spec.content, "\n")
    parent_chain = snapshot_parent_chain(
        root,
        target,
        require_complete=False,
        error_type=BootstrapConflict,
    )
    return PlannedChange(
        kind="entry",
        relative_path=spec.path,
        state="planned_create",
        pre_sha256=None,
        planned_post_sha256=sha256_bytes(block),
        target=target,
        payload=block,
        parent_chain=parent_chain,
    )


def build_plan(root: Path, manifest: ApprovedManifest) -> list[PlannedChange]:
    require_approved_root(root, manifest.root_identity, BootstrapConflict)
    declared_directories = {path_key(path) for path in manifest.directories}
    changes: list[PlannedChange] = []

    for path_text in sorted(
        manifest.directories,
        key=lambda value: (len(PurePosixPath(value).parts), path_key(value)),
    ):
        ensure_not_frozen(path_text, manifest.frozen_paths)
        ensure_declared_parent(root, path_text, declared_directories)
        target = target_path(root, path_text)
        parent_chain = snapshot_parent_chain(
            root,
            target,
            require_complete=False,
            error_type=BootstrapConflict,
        )
        target_identity: PathIdentity | None = None
        if os.path.lexists(target):
            try:
                info = os.stat(target, follow_symlinks=False)
            except OSError as exc:
                raise BootstrapConflict(
                    f"cannot bind declared directory {path_text!r}: {exc}"
                ) from exc
            if has_reparse_or_link_identity(info) or not stat.S_ISDIR(info.st_mode):
                raise BootstrapConflict(
                    f"declared directory target is not a non-reparse directory: {path_text!r}"
                )
            target_identity = path_identity(info)
            state = "existing"
        else:
            state = "planned_create"
        changes.append(
            PlannedChange(
                kind="directory",
                relative_path=path_text,
                state=state,
                target=target,
                target_identity=target_identity,
                parent_chain=parent_chain,
            )
        )

    for spec in sorted(manifest.files, key=lambda item: path_key(item.path)):
        ensure_not_frozen(spec.path, manifest.frozen_paths)
        ensure_declared_parent(root, spec.path, declared_directories)
        target = target_path(root, spec.path)
        if os.path.lexists(target):
            raw, snapshot, parent_chain = read_bound_file(
                root,
                target,
                spec.path,
                error_type=BootstrapConflict,
            )
            pre_hash = snapshot.sha256
            if raw != spec.content:
                raise BootstrapConflict(
                    f"existing control file is not byte-identical: {spec.path!r}"
                )
            changes.append(
                PlannedChange(
                    kind="control_file",
                    relative_path=spec.path,
                    state="unchanged",
                    pre_sha256=pre_hash,
                    planned_post_sha256=pre_hash,
                    target=target,
                    target_identity=snapshot.identity,
                    pre_snapshot=snapshot,
                    parent_chain=parent_chain,
                )
            )
        else:
            parent_chain = snapshot_parent_chain(
                root,
                target,
                require_complete=False,
                error_type=BootstrapConflict,
            )
            changes.append(
                PlannedChange(
                    kind="control_file",
                    relative_path=spec.path,
                    state="planned_create",
                    pre_sha256=None,
                    planned_post_sha256=spec.content_sha256,
                    target=target,
                    payload=spec.content,
                    parent_chain=parent_chain,
                )
            )

    ensure_not_frozen(manifest.entry.path, manifest.frozen_paths)
    ensure_declared_parent(root, manifest.entry.path, declared_directories)
    changes.append(plan_entry(root, manifest.entry))
    return changes


def write_all(descriptor: int, payload: bytes) -> None:
    remaining = memoryview(payload)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise ApplyError("filesystem returned a zero-length write")
        remaining = remaining[written:]


def descriptor_actual_path(descriptor: int, fallback: Path) -> str | None:
    """Best-effort final path for recovery reporting; never used as an authority."""
    if os.name == "nt":
        try:
            import msvcrt

            handle = msvcrt.get_osfhandle(descriptor)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            function = kernel32.GetFinalPathNameByHandleW
            function.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
            function.restype = ctypes.c_uint32
            needed = function(handle, None, 0, 0)
            if needed:
                buffer = ctypes.create_unicode_buffer(needed + 1)
                written = function(handle, buffer, len(buffer), 0)
                if written and written < len(buffer):
                    value = buffer.value
                    if value.startswith("\\\\?\\UNC\\"):
                        return "\\\\" + value[8:]
                    if value.startswith("\\\\?\\"):
                        return value[4:]
                    return value
        except (ImportError, OSError, ValueError):
            return None
    else:
        descriptor_link = Path(f"/proc/self/fd/{descriptor}")
        try:
            if descriptor_link.exists():
                return os.readlink(descriptor_link)
        except OSError:
            return None
    try:
        return str(fallback.resolve(strict=False))
    except OSError:
        return None


def recover_opened_identity_path(
    root: Path,
    descriptor: int,
    fallback: Path,
    identity: PathIdentity,
) -> str | None:
    """Prefer a currently resolvable path to the opened identity for recovery output."""
    reported = descriptor_actual_path(descriptor, fallback)
    if reported is not None:
        try:
            if path_identity(os.stat(reported, follow_symlinks=False)) == identity:
                return reported
        except OSError:
            pass
    inspected = 0
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        retained_directories: list[str] = []
        for name in directory_names:
            candidate = Path(directory) / name
            try:
                info = os.stat(candidate, follow_symlinks=False)
            except OSError:
                continue
            if not has_reparse_or_link_identity(info):
                retained_directories.append(name)
        directory_names[:] = retained_directories
        for name in file_names:
            inspected += 1
            if inspected > 10000:
                return reported
            candidate = Path(directory) / name
            try:
                if path_identity(os.stat(candidate, follow_symlinks=False)) == identity:
                    return str(candidate)
            except OSError:
                continue
    return reported


def forget_recovery(
    recovery_items: list[RecoveryItem], relative_path: str, kind: str
) -> None:
    recovery_items[:] = [
        item
        for item in recovery_items
        if not (item.relative_path == relative_path and item.kind == kind)
    ]


def copy_entry_metadata(
    source: Path,
    source_snapshot: FileSnapshot,
    destination_descriptor: int,
) -> None:
    """Preserve POSIX owner/mode/xattrs before exchange; Windows ReplaceFile owns metadata."""
    if os.name == "nt":
        return
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    source_descriptor: int | None = None
    try:
        source_descriptor = os.open(source, flags)
        source_info = os.fstat(source_descriptor)
        require_regular_single_link(source_info, str(source), ApplyError)
        if path_identity(source_info) != source_snapshot.identity:
            raise ApplyError("entry identity changed while copying metadata")
        fchmod = getattr(os, "fchmod", None)
        if callable(fchmod):
            fchmod(destination_descriptor, stat.S_IMODE(source_info.st_mode))
        fchown = getattr(os, "fchown", None)
        if callable(fchown):
            fchown(destination_descriptor, int(source_info.st_uid), int(source_info.st_gid))
        listxattr = getattr(os, "listxattr", None)
        getxattr = getattr(os, "getxattr", None)
        setxattr = getattr(os, "setxattr", None)
        if all(callable(item) for item in (listxattr, getxattr, setxattr)):
            for name in listxattr(source_descriptor):
                setxattr(destination_descriptor, name, getxattr(source_descriptor, name))
        destination_info = os.fstat(destination_descriptor)
        if (
            stat.S_IMODE(destination_info.st_mode) != stat.S_IMODE(source_info.st_mode)
            or int(destination_info.st_uid) != int(source_info.st_uid)
            or int(destination_info.st_gid) != int(source_info.st_gid)
        ):
            raise ApplyError("entry owner or mode was not preserved on replacement temp")
    except ApplyError:
        raise
    except OSError as exc:
        raise ApplyError(f"cannot preserve entry mode/owner/xattrs: {exc}") from exc
    finally:
        if source_descriptor is not None:
            os.close(source_descriptor)


def write_new_file(
    root: Path,
    manifest: ApprovedManifest,
    change: PlannedChange,
    recovery_items: list[RecoveryItem],
) -> None:
    assert change.target is not None and change.payload is not None
    require_approved_root(root, manifest.root_identity, ApplyError)
    parent_before = verify_parent_chain(
        root,
        change.target,
        change.parent_chain,
        require_complete=True,
        error_type=ApplyError,
    )
    target_path(root, change.relative_path, ApplyError)
    if os.path.lexists(change.target):
        raise ApplyError(f"target appeared after preflight: {change.relative_path!r}")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | int(getattr(os, "O_BINARY", 0))
    descriptor: int | None = None
    try:
        descriptor = os.open(change.target, flags, 0o666)
        change.state = "created_unverified"
        opened = os.fstat(descriptor)
        require_regular_single_link(opened, change.relative_path, ApplyError)
        created_identity = path_identity(opened)
        recovery_items.append(
            RecoveryItem(
                change.relative_path,
                "opened_creation",
                "inspect the exact opened file; its parent mapping may have changed",
                actual_path=descriptor_actual_path(descriptor, change.target),
                identity=created_identity,
            )
        )
        path_opened = os.stat(change.target, follow_symlinks=False)
        require_regular_single_link(path_opened, change.relative_path, ApplyError)
        if path_identity(path_opened) != created_identity:
            raise ApplyError(
                f"new-file identity differs between handle and path: {change.relative_path!r}"
            )
        verify_parent_chain(
            root,
            change.target,
            parent_before,
            require_complete=True,
            error_type=ApplyError,
        )
        write_all(descriptor, change.payload)
        os.fsync(descriptor)
        written = os.fstat(descriptor)
        require_regular_single_link(written, change.relative_path, ApplyError)
        if path_identity(written) != created_identity or int(written.st_size) != len(
            change.payload
        ):
            raise ApplyError(
                f"new-file identity or size changed during write: {change.relative_path!r}"
            )
        written_snapshot = file_snapshot(written, change.payload)
        recovery_items.append(
            RecoveryItem(
                change.relative_path,
                "opened_creation",
                "inspect the exact opened file; its parent mapping may have changed",
                actual_path=descriptor_actual_path(descriptor, change.target),
                identity=written_snapshot.identity,
                sha256=written_snapshot.sha256,
            )
        )
    except FileExistsError as exc:
        raise ApplyError(f"target appeared after preflight: {change.relative_path!r}") from exc
    except ApplyError:
        raise
    except OSError as exc:
        raise ApplyError(f"cannot create {change.relative_path!r}: {exc}") from exc
    finally:
        if descriptor is not None:
            try:
                final_info = os.fstat(descriptor)
                recovery_items.append(
                    RecoveryItem(
                        change.relative_path,
                        "opened_creation",
                        "inspect the exact opened file; its parent mapping may have changed",
                        actual_path=recover_opened_identity_path(
                            root,
                            descriptor,
                            change.target,
                            path_identity(final_info),
                        ),
                        identity=path_identity(final_info),
                    )
                )
            except OSError:
                pass
            os.close(descriptor)

    observed_bytes, observed_snapshot, parent_after = read_bound_file(
        root,
        change.target,
        change.relative_path,
        expected_parent_chain=parent_before,
        error_type=ApplyError,
    )
    if (
        observed_snapshot.identity != written_snapshot.identity
        or observed_bytes != change.payload
        or observed_snapshot.sha256 != change.planned_post_sha256
        or parent_after != parent_before
    ):
        raise ApplyError(f"post-write identity/hash mismatch: {change.relative_path!r}")
    change.target_identity = observed_snapshot.identity
    change.observed_post_sha256 = observed_snapshot.sha256
    change.state = "created"
    forget_recovery(recovery_items, change.relative_path, "opened_creation")


def create_entry_temp(
    root: Path,
    manifest: ApprovedManifest,
    change: PlannedChange,
    recovery_items: list[RecoveryItem],
    parent_chain: tuple[BoundPath, ...],
) -> tuple[Path, FileSnapshot]:
    assert change.target is not None and change.payload is not None
    require_approved_root(root, manifest.root_identity, ApplyError)
    verify_parent_chain(
        root,
        change.target,
        parent_chain,
        require_complete=True,
        error_type=ApplyError,
    )
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{change.target.name}.manage-workspace-memory-",
            suffix=".tmp",
            dir=change.target.parent,
        )
    except OSError as exc:
        raise ApplyError(f"cannot create same-directory exclusive entry temp: {exc}") from exc
    temporary = Path(temporary_name)
    temporary_relative = workspace_relative(root, temporary)
    recovery_items.append(
        RecoveryItem(
            temporary_relative,
            "exclusive_temp",
            "inspect and remove only after reconciling the entry replacement",
        )
    )
    try:
        opened = os.fstat(descriptor)
        require_regular_single_link(opened, temporary_relative, ApplyError)
        temporary_identity = path_identity(opened)
        recovery_items.append(
            RecoveryItem(
                temporary_relative,
                "exclusive_temp",
                "inspect and remove only after reconciling the entry replacement",
                actual_path=descriptor_actual_path(descriptor, temporary),
                identity=temporary_identity,
            )
        )
        path_opened = os.stat(temporary, follow_symlinks=False)
        require_regular_single_link(path_opened, temporary_relative, ApplyError)
        if path_identity(path_opened) != temporary_identity:
            raise ApplyError("exclusive temp identity differs between handle and path")
        verify_parent_chain(
            root,
            change.target,
            parent_chain,
            require_complete=True,
            error_type=ApplyError,
        )
        write_all(descriptor, change.payload)
        if change.pre_snapshot is not None:
            copy_entry_metadata(change.target, change.pre_snapshot, descriptor)
        os.fsync(descriptor)
        written = os.fstat(descriptor)
        require_regular_single_link(written, temporary_relative, ApplyError)
        if path_identity(written) != temporary_identity or int(written.st_size) != len(
            change.payload
        ):
            raise ApplyError("exclusive temp identity or size changed during write")
        snapshot = file_snapshot(written, change.payload)
        recovery_items.append(
            RecoveryItem(
                temporary_relative,
                "exclusive_temp",
                "inspect and remove only after reconciling the entry replacement",
                actual_path=descriptor_actual_path(descriptor, temporary),
                identity=snapshot.identity,
                sha256=snapshot.sha256,
            )
        )
    except ApplyError:
        raise
    except OSError as exc:
        raise ApplyError(f"cannot write exclusive entry temp: {exc}") from exc
    finally:
        try:
            final_info = os.fstat(descriptor)
            recovery_items.append(
                RecoveryItem(
                    temporary_relative,
                    "exclusive_temp",
                    "inspect and remove only after reconciling the entry replacement",
                    actual_path=recover_opened_identity_path(
                        root,
                        descriptor,
                        temporary,
                        path_identity(final_info),
                    ),
                    identity=path_identity(final_info),
                )
            )
        except OSError:
            pass
        os.close(descriptor)

    raw, observed, observed_parent = read_bound_file(
        root,
        temporary,
        temporary_relative,
        expected_parent_chain=parent_chain,
        error_type=ApplyError,
    )
    if (
        raw != change.payload
        or observed.identity != snapshot.identity
        or observed.sha256 != change.planned_post_sha256
        or observed_parent != parent_chain
    ):
        raise ApplyError("exclusive entry temp failed identity/hash verification")
    return temporary, observed


def reserve_vacant_backup_path(target: Path) -> Path:
    """Choose a same-directory backup name; a later squatter makes ReplaceFile fail closed."""
    try:
        descriptor, name = tempfile.mkstemp(
            prefix=f".{target.name}.manage-workspace-memory-replaced-",
            suffix=".bak",
            dir=target.parent,
        )
        os.close(descriptor)
        os.unlink(name)
    except OSError as exc:
        raise ApplyError(f"cannot reserve replacement-backup name: {exc}") from exc
    return Path(name)


def atomic_recoverable_exchange(
    root: Path,
    target: Path,
    replacement: Path,
    recovery_items: list[RecoveryItem],
) -> Path:
    """Install replacement while retaining the displaced target at a known path."""
    replacement_relative = workspace_relative(root, replacement)
    if os.name == "nt":
        backup = reserve_vacant_backup_path(target)
        backup_relative = workspace_relative(root, backup)
        recovery_items.append(
            RecoveryItem(
                backup_relative,
                "replacement_backup",
                "retain until the displaced entry identity and replacement are verified",
                actual_path=str(backup),
            )
        )
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        replace_file = kernel32.ReplaceFileW
        replace_file.argtypes = [
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        replace_file.restype = ctypes.c_int
        succeeded = replace_file(str(target), str(replacement), str(backup), 1, None, None)
        if not succeeded:
            error_code = ctypes.get_last_error()
            raise ApplyError(
                "recoverable ReplaceFileW entry replacement failed; all observed helper "
                f"artifacts were retained (winerror={error_code})"
            )
        forget_recovery(recovery_items, replacement_relative, "exclusive_temp")
        return backup

    if sys.platform.startswith("linux"):
        library = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(library, "renameat2", None)
        if renameat2 is None:
            raise ApplyError(
                "platform lacks renameat2(RENAME_EXCHANGE); refusing a lossy entry replacement"
            )
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100,
            os.fsencode(target),
            -100,
            os.fsencode(replacement),
            2,
        )
        if result != 0:
            error_code = ctypes.get_errno()
            raise ApplyError(
                "recoverable renameat2 exchange failed; replacement temp was retained "
                f"(errno={error_code})"
            )
        forget_recovery(recovery_items, replacement_relative, "exclusive_temp")
        recovery_items.append(
            RecoveryItem(
                replacement_relative,
                "replacement_backup",
                "retain until the displaced entry identity and replacement are verified",
                actual_path=str(replacement),
            )
        )
        return replacement

    if sys.platform == "darwin":
        library = ctypes.CDLL("libSystem.B.dylib", use_errno=True)
        renamex_np = getattr(library, "renamex_np", None)
        if renamex_np is None:
            raise ApplyError(
                "platform lacks renamex_np(RENAME_SWAP); refusing a lossy entry replacement"
            )
        renamex_np.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        renamex_np.restype = ctypes.c_int
        if renamex_np(os.fsencode(target), os.fsencode(replacement), 0x00000002) != 0:
            error_code = ctypes.get_errno()
            raise ApplyError(
                "recoverable renamex_np exchange failed; replacement temp was retained "
                f"(errno={error_code})"
            )
        forget_recovery(recovery_items, replacement_relative, "exclusive_temp")
        recovery_items.append(
            RecoveryItem(
                replacement_relative,
                "replacement_backup",
                "retain until the displaced entry identity and replacement are verified",
                actual_path=str(replacement),
            )
        )
        return replacement

    raise ApplyError(
        "platform has no supported recoverable atomic exchange; refusing a lossy entry replacement"
    )


def delete_verified_backup(
    root: Path,
    backup: Path,
    backup_snapshot: FileSnapshot,
    parent_chain: tuple[BoundPath, ...],
    recovery_items: list[RecoveryItem],
) -> None:
    backup_relative = workspace_relative(root, backup)
    _raw, rebound, rebound_parent = read_bound_file(
        root,
        backup,
        backup_relative,
        expected_parent_chain=parent_chain,
        error_type=ApplyError,
    )
    if (
        rebound.identity != backup_snapshot.identity
        or rebound.sha256 != backup_snapshot.sha256
        or rebound_parent != parent_chain
    ):
        raise ApplyError("replacement backup changed before verified cleanup; retaining it")
    try:
        os.unlink(backup)
    except OSError as exc:
        raise ApplyError(f"verified replacement backup could not be removed: {exc}") from exc
    forget_recovery(recovery_items, backup_relative, "replacement_backup")


def replace_entry(
    root: Path,
    manifest: ApprovedManifest,
    change: PlannedChange,
    recovery_items: list[RecoveryItem],
) -> None:
    assert (
        change.target is not None and change.payload is not None and change.pre_snapshot is not None
    )
    require_approved_root(root, manifest.root_identity, ApplyError)
    current, current_snapshot, parent_chain = read_bound_file(
        root,
        change.target,
        change.relative_path,
        expected_snapshot=change.pre_snapshot,
        expected_parent_chain=change.parent_chain,
        error_type=ApplyError,
    )
    if current_snapshot.sha256 != change.pre_sha256:
        raise ApplyError(
            f"entry changed after preflight; refusing replacement: {change.relative_path!r}"
        )
    temporary, temporary_snapshot = create_entry_temp(
        root,
        manifest,
        change,
        recovery_items,
        parent_chain,
    )

    current_again, current_again_snapshot, parent_again = read_bound_file(
        root,
        change.target,
        change.relative_path,
        expected_snapshot=change.pre_snapshot,
        expected_parent_chain=parent_chain,
        error_type=ApplyError,
    )
    if current_again != current or current_again_snapshot != current_snapshot:
        raise ApplyError(f"entry changed before atomic replacement: {change.relative_path!r}")
    if parent_again != parent_chain:
        raise ApplyError(
            f"entry parent identity changed before atomic replacement: {change.relative_path!r}"
        )
    target_path(root, change.relative_path, ApplyError)
    require_approved_root(root, manifest.root_identity, ApplyError)
    verify_parent_chain(
        root,
        change.target,
        parent_chain,
        require_complete=True,
        error_type=ApplyError,
    )
    backup = atomic_recoverable_exchange(
        root,
        change.target,
        temporary,
        recovery_items,
    )
    change.state = "replacement_unverified"

    backup_relative = workspace_relative(root, backup)
    displaced, displaced_snapshot, displaced_parent = read_bound_file(
        root,
        backup,
        backup_relative,
        expected_parent_chain=parent_chain,
        error_type=ApplyError,
    )
    recovery_items.append(
        RecoveryItem(
            backup_relative,
            "replacement_backup",
            "reconcile the exact displaced entry before any cleanup",
            actual_path=str(backup),
            identity=displaced_snapshot.identity,
            sha256=displaced_snapshot.sha256,
        )
    )
    if (
        displaced != current
        or displaced_snapshot.identity != current_snapshot.identity
        or displaced_snapshot.sha256 != current_snapshot.sha256
        or displaced_parent != parent_chain
    ):
        raise ApplyError(
            "entry changed in the final replacement window; the displaced concurrent file "
            "was retained exactly as replacement_backup and recovery is required"
        )

    require_approved_root(root, manifest.root_identity, ApplyError)
    observed, observed_snapshot, parent_after = read_bound_file(
        root,
        change.target,
        change.relative_path,
        expected_parent_chain=parent_chain,
        error_type=ApplyError,
    )
    if (
        observed != change.payload
        or observed_snapshot.identity != temporary_snapshot.identity
        or observed_snapshot.link_count != 1
        or observed_snapshot.sha256 != change.planned_post_sha256
        or parent_after != parent_chain
    ):
        raise ApplyError(f"post-replacement identity/hash mismatch: {change.relative_path!r}")
    change.target_identity = observed_snapshot.identity
    change.observed_post_sha256 = observed_snapshot.sha256
    delete_verified_backup(
        root,
        backup,
        displaced_snapshot,
        parent_chain,
        recovery_items,
    )
    change.state = "merged"


def calculate_plan_sha256(
    root_identity: RootIdentity,
    manifest: ApprovedManifest,
    changes: Sequence[PlannedChange],
) -> str:
    payload = {
        "contract": "manage-workspace-memory-bootstrap-plan-v1",
        "approved_manifest_sha256": manifest.approved_manifest_sha256,
        "root_identity": root_identity.public(),
        "changes": [change.public() for change in changes],
    }
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8", errors="strict")
    return sha256_bytes(canonical)


def bind_post_creation_parent_chains(
    root: Path,
    changes: Sequence[PlannedChange],
) -> None:
    declared_directory_identities = {
        path_key(change.relative_path): change.target_identity
        for change in changes
        if change.kind == "directory" and change.target_identity is not None
    }
    for change in changes:
        if change.kind == "directory" or change.target is None:
            continue
        observed = snapshot_parent_chain(
            root,
            change.target,
            require_complete=True,
            error_type=ApplyError,
        )
        for component in observed:
            if component.relative_path == ".":
                continue
            expected = declared_directory_identities.get(path_key(component.relative_path))
            if expected is not None and component.identity != expected:
                raise ApplyError(
                    f"declared parent directory identity changed after creation: "
                    f"{component.relative_path!r}"
                )
        if (
            len(observed) < len(change.parent_chain)
            or tuple(observed[: len(change.parent_chain)]) != change.parent_chain
        ):
            raise ApplyError(
                f"parent-chain identity changed after directory creation: "
                f"{workspace_relative(root, change.target.parent)!r}"
            )
        change.parent_chain = observed


def apply_plan(
    root: Path,
    manifest_path: Path,
    manifest: ApprovedManifest,
    changes: list[PlannedChange],
    recovery_items: list[RecoveryItem],
) -> None:
    for change in changes:
        if change.kind != "directory":
            continue
        assert change.target is not None
        require_approved_root(root, manifest.root_identity, ApplyError)
        require_manifest_disjoint(root, manifest_path, manifest, ApplyError)
        if change.state == "planned_create":
            parent_before = verify_parent_chain(
                root,
                change.target,
                change.parent_chain,
                require_complete=True,
                error_type=ApplyError,
            )
            target_path(root, change.relative_path, ApplyError)
            if os.path.lexists(change.target):
                raise ApplyError(f"directory appeared after preflight: {change.relative_path!r}")
            try:
                change.target.mkdir()
            except FileExistsError as exc:
                raise ApplyError(
                    f"directory appeared after preflight: {change.relative_path!r}"
                ) from exc
            except OSError as exc:
                raise ApplyError(
                    f"cannot create directory {change.relative_path!r}: {exc}"
                ) from exc
            change.state = "created"
            try:
                actual_directory = str(change.target.resolve(strict=False))
            except OSError:
                actual_directory = None
            recovery_items.append(
                RecoveryItem(
                    change.relative_path,
                    "created_directory_unverified",
                    "inspect the created directory; its parent mapping may have changed",
                    actual_path=actual_directory,
                )
            )
            try:
                created = os.stat(change.target, follow_symlinks=False)
            except OSError as exc:
                raise ApplyError(
                    f"cannot bind created directory {change.relative_path!r}: {exc}"
                ) from exc
            if has_reparse_or_link_identity(created) or not stat.S_ISDIR(created.st_mode):
                raise ApplyError(
                    f"created directory became a reparse or non-directory target: "
                    f"{change.relative_path!r}"
                )
            change.target_identity = path_identity(created)
            recovery_items.append(
                RecoveryItem(
                    change.relative_path,
                    "created_directory_unverified",
                    "inspect the created directory; its parent mapping may have changed",
                    actual_path=actual_directory,
                    identity=change.target_identity,
                )
            )
            verify_parent_chain(
                root,
                change.target,
                parent_before,
                require_complete=True,
                error_type=ApplyError,
            )
            forget_recovery(
                recovery_items,
                change.relative_path,
                "created_directory_unverified",
            )
        elif change.state == "existing":
            target_path(root, change.relative_path, ApplyError)
            try:
                observed = os.stat(change.target, follow_symlinks=False)
            except OSError as exc:
                raise ApplyError(
                    f"cannot rebind existing directory {change.relative_path!r}: {exc}"
                ) from exc
            if (
                has_reparse_or_link_identity(observed)
                or not stat.S_ISDIR(observed.st_mode)
                or path_identity(observed) != change.target_identity
            ):
                raise ApplyError(
                    f"existing directory identity changed after preflight: {change.relative_path!r}"
                )

    bind_post_creation_parent_chains(root, changes)

    for change in changes:
        if change.kind == "directory":
            continue
        require_manifest_disjoint(root, manifest_path, manifest, ApplyError)
        if change.state == "planned_create":
            write_new_file(root, manifest, change, recovery_items)
        elif change.state in {"planned_merge", "planned_update"}:
            replace_entry(root, manifest, change, recovery_items)
        elif change.state == "unchanged":
            assert change.target is not None and change.pre_snapshot is not None
            require_approved_root(root, manifest.root_identity, ApplyError)
            _raw, observed, _parent = read_bound_file(
                root,
                change.target,
                change.relative_path,
                expected_snapshot=change.pre_snapshot,
                expected_parent_chain=change.parent_chain,
                error_type=ApplyError,
            )
            if observed.sha256 != change.planned_post_sha256:
                raise ApplyError(
                    f"unchanged target changed after preflight: {change.relative_path!r}"
                )
            change.observed_post_sha256 = observed.sha256


def render_success(
    *,
    root: Path,
    manifest_path: Path,
    manifest: ApprovedManifest,
    changes: Sequence[PlannedChange],
    apply: bool,
    plan_sha256: str,
) -> str:
    changed_states = {"planned_create", "planned_merge", "planned_update"}
    if apply:
        changed_states = {"created", "merged"}
    payload = {
        "applied": apply,
        "approval": {
            "approved_at": manifest.approved_at,
            "approved_by_role": manifest.approved_by_role,
            "decision_id": manifest.decision_id,
            "manifest_sha256": manifest.approved_manifest_sha256,
        },
        "change_count": sum(change.state in changed_states for change in changes),
        "changes": [change.public() for change in changes],
        "manifest": str(manifest_path),
        "mode": "apply" if apply else "dry-run",
        "ok": True,
        "plan_sha256": plan_sha256,
        "root": str(root),
        "root_identity": manifest.root_identity.public(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def recovery_manifest(
    changes: Sequence[PlannedChange],
    recovery_items: Sequence[RecoveryItem],
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    persisted_states = {
        "created",
        "created_unverified",
        "merged",
        "replacement_unverified",
    }
    persisted = [change.public() for change in changes if change.state in persisted_states]
    required: list[RecoveryItem] = list(recovery_items)
    for change in changes:
        if change.state not in persisted_states:
            continue
        if change.state == "created":
            action = "verify the declared creation, then retain it or remove it separately"
        elif change.state == "merged":
            action = "verify the managed entry replacement before retrying"
        else:
            action = "inspect identity and content; do not overwrite or retry blindly"
        required.append(RecoveryItem(change.relative_path, change.state, action))
    deduplicated: dict[tuple[str, str], RecoveryItem] = {}
    for item in required:
        deduplicated[(item.relative_path, item.kind)] = item
    return persisted, [item.public() for item in deduplicated.values()]


def render_error(
    kind: str,
    message: str,
    *,
    mode: str,
    changes: Sequence[PlannedChange],
    recovery_items: Sequence[RecoveryItem],
    plan_sha256: str | None,
) -> str:
    persisted, recovery_required = recovery_manifest(changes, recovery_items)
    return json.dumps(
        {
            "changes": [change.public() for change in changes],
            "error": message,
            "error_kind": kind,
            "mode": mode,
            "ok": False,
            "persisted_changes": persisted,
            "plan_sha256": plan_sha256,
            "recovery_required": recovery_required,
            "writes_started": bool(persisted or recovery_required),
        },
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run or apply an already approved, create-only workspace-memory "
            "bootstrap manifest. The default is read-only dry-run."
        )
    )
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument(
        "--inspect-root",
        action="store_true",
        help="Print the normalized root identity needed by a pending manifest.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the preflighted create-and-managed-block plan.",
    )
    parser.add_argument(
        "--expected-plan-sha256",
        help="On apply, require an exact plan hash from a prior dry run.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    configure_utf8_streams()
    arguments = build_parser().parse_args(argv)
    changes: list[PlannedChange] = []
    recovery_items: list[RecoveryItem] = []
    plan_sha256: str | None = None
    mode = "apply" if arguments.apply else "dry-run"
    try:
        root = resolve_root(arguments.root)
        if arguments.inspect_root:
            if arguments.manifest is not None or arguments.apply or arguments.expected_plan_sha256:
                raise ManifestError(
                    "--inspect-root cannot be combined with --manifest, --apply, or "
                    "--expected-plan-sha256"
                )
            identity = inspect_root_identity(root)
            print(
                json.dumps(
                    {"ok": True, "root": str(root), "root_identity": identity.public()},
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        if arguments.manifest is None:
            raise ManifestError("--manifest is required unless --inspect-root is used")
        if arguments.expected_plan_sha256 is not None and not arguments.apply:
            raise ManifestError("--expected-plan-sha256 is valid only with --apply")
        manifest_path = arguments.manifest.expanduser().resolve(strict=True)
        manifest = parse_manifest(load_json_manifest(manifest_path))
        require_manifest_disjoint(root, manifest_path, manifest)
        root_identity = require_approved_root(root, manifest.root_identity)
        changes = build_plan(root, manifest)
        plan_sha256 = calculate_plan_sha256(root_identity, manifest, changes)
        if arguments.expected_plan_sha256 is not None:
            expected_plan_sha256 = validate_sha256(
                arguments.expected_plan_sha256,
                "--expected-plan-sha256",
            )
            if expected_plan_sha256 != plan_sha256:
                raise BootstrapConflict(
                    "current plan hash differs from the reviewed dry-run plan hash"
                )
        if arguments.apply:
            require_manifest_disjoint(root, manifest_path, manifest, ApplyError)
            apply_plan(root, manifest_path, manifest, changes, recovery_items)
    except ManifestError as exc:
        print(
            render_error(
                "manifest",
                str(exc),
                mode=mode,
                changes=changes,
                recovery_items=recovery_items,
                plan_sha256=plan_sha256,
            ),
            file=sys.stderr,
        )
        return 2
    except BootstrapConflict as exc:
        print(
            render_error(
                "conflict",
                str(exc),
                mode=mode,
                changes=changes,
                recovery_items=recovery_items,
                plan_sha256=plan_sha256,
            ),
            file=sys.stderr,
        )
        return 1
    except ApplyError as exc:
        print(
            render_error(
                "apply",
                str(exc),
                mode=mode,
                changes=changes,
                recovery_items=recovery_items,
                plan_sha256=plan_sha256,
            ),
            file=sys.stderr,
        )
        return 1
    except OSError as exc:
        print(
            render_error(
                "filesystem",
                str(exc),
                mode=mode,
                changes=changes,
                recovery_items=recovery_items,
                plan_sha256=plan_sha256,
            ),
            file=sys.stderr,
        )
        return 2
    assert plan_sha256 is not None
    print(
        render_success(
            root=root,
            manifest_path=manifest_path,
            manifest=manifest,
            changes=changes,
            apply=arguments.apply,
            plan_sha256=plan_sha256,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
