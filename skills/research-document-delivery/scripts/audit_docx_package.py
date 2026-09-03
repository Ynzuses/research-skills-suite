#!/usr/bin/env python3
"""Read-only structural audit for one or more DOCX (Open Packaging) files.

The audit deliberately does not extract archive members and does not modify the
input.  It checks package integrity and selected WordprocessingML structures;
it does not prove rendered appearance, pagination, or semantic correctness.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from io import BytesIO
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import sys
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit
import zipfile
import xml.etree.ElementTree as ET
import zlib


SCHEMA_VERSION = 1
MAX_ENTRIES = 20_000
MAX_MEMBER_UNCOMPRESSED = 256 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 512 * 1024 * 1024
MAX_XML_MEMBER = 32 * 1024 * 1024
MAX_XML_TOTAL = 128 * 1024 * 1024
MAX_COMPRESSION_RATIO = 10_000
DETAIL_LIMIT = 50

CONTENT_TYPES_PART = "[Content_Types].xml"
ROOT_RELS_PART = "_rels/.rels"
DOCUMENT_PART = "word/document.xml"
DOCUMENT_RELS_PART = "word/_rels/document.xml.rels"

CONTENT_TYPES_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/content-types"
)
RELATIONSHIPS_NAMESPACE = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
OFFICE_DOCUMENT_RELATIONSHIP_TYPES = {
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
    "http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument",
}
MAIN_DOCUMENT_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
}

WORD_NAMESPACES = {
    "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "http://purl.oclc.org/ooxml/wordprocessingml/main",
}
MATH_NAMESPACES = {
    "http://schemas.openxmlformats.org/officeDocument/2006/math",
    "http://purl.oclc.org/ooxml/officeDocument/math",
}
TRACKED_CHANGE_NAMES = ("ins", "del", "moveFrom", "moveTo")
FIELD_CODE_NAMES = ("fldChar", "instrText", "fldSimple")
COMMENT_MARKER_NAMES = (
    "commentRangeStart",
    "commentRangeEnd",
    "commentReference",
)
FAMILY_TOKENS = (
    "comment",
    "people",
    "person",
    "presence",
    "author",
    "reply",
    "replies",
)
XML_DECLARATION_RE = re.compile(br"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
XML_DECLARATION_TEXT_RE = re.compile(r"<!\s*(?:DOCTYPE|ENTITY)\b", re.IGNORECASE)
ENCODED_SEPARATOR_RE = re.compile(r"%(?:2f|5c)", re.IGNORECASE)


class AuditReadError(Exception):
    """Raised when a package member cannot be read safely."""


def _configure_utf8_stdio() -> None:
    """Keep non-ASCII paths legible on PowerShell and redirected output."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (AttributeError, OSError, ValueError):
                pass


def _absolute_display_path(path: Path) -> str:
    try:
        return str(path.resolve(strict=False))
    except (OSError, RuntimeError):
        return os.path.abspath(os.fspath(path))


def _new_result(path: Path) -> dict[str, Any]:
    return {
        "path": _absolute_display_path(path),
        "status": "ok",
        "scope": (
            "Read-only package-structure audit; this does not verify rendered "
            "appearance, pagination, or semantic correctness."
        ),
        "package": {
            "entries": 0,
            "file_entries": 0,
            "directory_entries": 0,
            "total_uncompressed_bytes": 0,
            "duplicate_entries": [],
            "case_collisions": [],
            "unsafe_entries": [],
            "rejected_for_safe_audit": False,
            "deep_audit_complete": False,
        },
        "metrics": {
            "parsed_xml_parts": [],
            "skipped_xml_parts": [],
            "tracked_changes": {name: 0 for name in TRACKED_CHANGE_NAMES},
            "field_codes": {name: 0 for name in FIELD_CODE_NAMES},
            "equations": {"oMath": 0, "oMathPara": 0},
            "footnotes": {"parts": [], "elements": 0},
            "endnotes": {"parts": [], "elements": 0},
            "comment_markers": {name: 0 for name in COMMENT_MARKER_NAMES},
            "comment_definitions": 0,
            "comment_family_parts": [],
            "comment_family_relationships": [],
            "comment_family_content_types": [],
            "external_relationships": [],
            "missing_relationship_targets": [],
        },
        "findings": [],
        "summary": {"errors": 0, "issues": 0, "info": 0},
    }


def _add_finding(
    result: dict[str, Any],
    severity: str,
    code: str,
    message: str,
    *,
    part: str | None = None,
    count: int | None = None,
    details: Any | None = None,
) -> None:
    finding: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if part is not None:
        finding["part"] = part
    if count is not None:
        finding["count"] = count
    if details is not None:
        finding["details"] = details
    result["findings"].append(finding)


def _limited_details(values: Iterable[Any]) -> list[Any]:
    items = list(values)
    return items[:DETAIL_LIMIT]


def _finish_result(result: dict[str, Any]) -> dict[str, Any]:
    severity_order = {"error": 0, "issue": 1, "info": 2}
    result["findings"].sort(
        key=lambda item: (
            severity_order.get(item["severity"], 99),
            item["code"],
            item.get("part", ""),
            item["message"],
        )
    )
    counts = Counter(item["severity"] for item in result["findings"])
    result["summary"] = {
        "errors": counts.get("error", 0),
        "issues": counts.get("issue", 0),
        "info": counts.get("info", 0),
    }
    if result["summary"]["errors"]:
        result["status"] = "read_error"
    elif result["summary"]["issues"]:
        result["status"] = "issues"
    else:
        result["status"] = "ok"
    return result


def _split_tag(tag: Any) -> tuple[str, str]:
    if not isinstance(tag, str):
        return "", ""
    if tag.startswith("{") and "}" in tag:
        namespace, local = tag[1:].split("}", 1)
        return namespace, local
    return "", tag


def _attribute(attributes: dict[str, str], local_name: str) -> str | None:
    for key, value in attributes.items():
        if _split_tag(key)[1] == local_name:
            return value
    return None


def _is_word_tag(tag: Any, local_name: str) -> bool:
    namespace, local = _split_tag(tag)
    return local == local_name and namespace in WORD_NAMESPACES


def _is_math_tag(tag: Any, local_name: str) -> bool:
    namespace, local = _split_tag(tag)
    return local == local_name and namespace in MATH_NAMESPACES


def _is_exact_tag(tag: Any, namespace: str, local_name: str) -> bool:
    actual_namespace, local = _split_tag(tag)
    return local == local_name and actual_namespace == namespace


def _has_family_token(value: str | None) -> bool:
    lowered = (value or "").casefold()
    return any(token in lowered for token in FAMILY_TOKENS)


def _is_family_part(part: str) -> bool:
    if part.casefold().endswith(".rels"):
        return False
    basename = posixpath.basename(part).casefold()
    return _has_family_token(basename)


def _is_base_comments_part(part: str) -> bool:
    return posixpath.basename(part).casefold() == "comments.xml"


def _decode_percent_layers(value: str, *, rounds: int = 3) -> str:
    """Decode enough layers to expose encoded separators used for evasion."""

    decoded = value
    for _ in range(rounds):
        next_value = unquote(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def _has_encoded_separator(value: str) -> bool:
    candidate = value
    for _ in range(3):
        if ENCODED_SEPARATOR_RE.search(candidate):
            return True
        next_value = unquote(candidate)
        if next_value == candidate:
            return False
        candidate = next_value
    return bool(ENCODED_SEPARATOR_RE.search(candidate))


def _canonical_zip_name(name: str) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not name:
        return "", ["empty member name"]
    if "\x00" in name:
        reasons.append("NUL byte in member name")
    if "\\" in name:
        reasons.append("backslash path separator")
    if _has_encoded_separator(name):
        reasons.append("percent-encoded path separator")
    converted = name.replace("\\", "/")
    directory = converted.endswith("/")
    body = converted[:-1] if directory else converted
    if body.startswith("/"):
        reasons.append("absolute member path")
    if re.match(r"^[A-Za-z]:", body):
        reasons.append("drive-qualified member path")
    segments = body.split("/") if body else []
    if any(segment == ".." for segment in segments):
        reasons.append("parent traversal segment")
    if any(segment in {"", "."} for segment in segments):
        reasons.append("empty or dot path segment")
    if any(":" in segment for segment in segments):
        reasons.append("colon in path segment")
    if any(segment.endswith((" ", ".")) for segment in segments):
        reasons.append("platform-ambiguous trailing space or dot")
    canonical = posixpath.normpath(body) if body else ""
    if canonical in {"", ".", ".."} or canonical.startswith("../"):
        reasons.append("member path resolves outside or lacks a package part")

    decoded = _decode_percent_layers(converted)
    decoded_body = decoded[:-1] if directory and decoded.endswith("/") else decoded
    decoded_segments = decoded_body.replace("\\", "/").split("/")
    if any(segment == ".." for segment in decoded_segments):
        reasons.append("percent-encoded parent traversal segment")
    if decoded_body.startswith(("/", "\\")) or re.match(
        r"^[A-Za-z]:", decoded_body
    ):
        reasons.append("percent-encoded absolute or drive-qualified path")
    return canonical, sorted(set(reasons))


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    if info.create_system != 3:
        return False
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)


def _read_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    if info.file_size > MAX_XML_MEMBER:
        raise AuditReadError(
            f"uncompressed XML member exceeds {MAX_XML_MEMBER} bytes"
        )
    chunks: list[bytes] = []
    size = 0
    try:
        with zf.open(info, "r") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_XML_MEMBER:
                    raise AuditReadError(
                        f"expanded XML member exceeds {MAX_XML_MEMBER} bytes"
                    )
                chunks.append(chunk)
    except (
        zipfile.BadZipFile,
        RuntimeError,
        OSError,
        EOFError,
        NotImplementedError,
        zlib.error,
    ) as exc:
        raise AuditReadError(str(exc)) from exc
    return b"".join(chunks)


def _parse_xml_part(part: str, data: bytes) -> dict[str, Any]:
    forbidden_declaration = bool(XML_DECLARATION_RE.search(data))
    if not forbidden_declaration and (
        data.startswith((b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff", b"\xff\xfe\x00\x00"))
        or b"\x00" in data[:256]
    ):
        for encoding in ("utf-16", "utf-32"):
            try:
                if XML_DECLARATION_TEXT_RE.search(data.decode(encoding)):
                    forbidden_declaration = True
                    break
            except UnicodeError:
                continue
    if forbidden_declaration:
        raise ValueError("DOCTYPE or ENTITY declaration is not permitted")

    parsed: dict[str, Any] = {
        "root": "",
        "root_namespace": "",
        "document_body_count": 0,
        "tracked": Counter(),
        "fields": Counter(),
        "equations": Counter(),
        "markers": {name: Counter() for name in COMMENT_MARKER_NAMES},
        "marker_missing_ids": Counter(),
        "definition_ids": Counter(),
        "definition_missing_ids": 0,
        "footnotes": 0,
        "endnotes": 0,
        "content_types": [],
        "relationships": [],
    }
    first = True
    depth = 0
    try:
        for event, element in ET.iterparse(BytesIO(data), events=("start", "end")):
            if event == "start":
                namespace, local = _split_tag(element.tag)
                if first:
                    parsed["root"] = local
                    parsed["root_namespace"] = namespace
                    first = False

                if (
                    part == DOCUMENT_PART
                    and depth == 1
                    and _is_word_tag(element.tag, "body")
                ):
                    parsed["document_body_count"] += 1

                for name in TRACKED_CHANGE_NAMES:
                    if _is_word_tag(element.tag, name):
                        parsed["tracked"][name] += 1
                for name in FIELD_CODE_NAMES:
                    if _is_word_tag(element.tag, name):
                        parsed["fields"][name] += 1
                for name in ("oMath", "oMathPara"):
                    if _is_math_tag(element.tag, name):
                        parsed["equations"][name] += 1
                for name in COMMENT_MARKER_NAMES:
                    if _is_word_tag(element.tag, name):
                        marker_id = _attribute(element.attrib, "id")
                        if marker_id is None:
                            parsed["marker_missing_ids"][name] += 1
                        else:
                            parsed["markers"][name][marker_id] += 1

                if _is_base_comments_part(part) and _is_word_tag(
                    element.tag, "comment"
                ):
                    comment_id = _attribute(element.attrib, "id")
                    if comment_id is None:
                        parsed["definition_missing_ids"] += 1
                    else:
                        parsed["definition_ids"][comment_id] += 1
                if posixpath.basename(part).casefold() == "footnotes.xml" and _is_word_tag(
                    element.tag, "footnote"
                ):
                    parsed["footnotes"] += 1
                if posixpath.basename(part).casefold() == "endnotes.xml" and _is_word_tag(
                    element.tag, "endnote"
                ):
                    parsed["endnotes"] += 1

                if part == CONTENT_TYPES_PART and (
                    _is_exact_tag(element.tag, CONTENT_TYPES_NAMESPACE, "Override")
                    or _is_exact_tag(element.tag, CONTENT_TYPES_NAMESPACE, "Default")
                ):
                    parsed["content_types"].append(
                        {
                            "kind": local,
                            "part_name": _attribute(element.attrib, "PartName"),
                            "extension": _attribute(element.attrib, "Extension"),
                            "content_type": _attribute(element.attrib, "ContentType"),
                        }
                    )
                if part.casefold().endswith(".rels") and _is_exact_tag(
                    element.tag, RELATIONSHIPS_NAMESPACE, "Relationship"
                ):
                    parsed["relationships"].append(
                        {
                            "id": _attribute(element.attrib, "Id"),
                            "type": _attribute(element.attrib, "Type"),
                            "target": _attribute(element.attrib, "Target"),
                            "target_mode": _attribute(element.attrib, "TargetMode"),
                        }
                    )
                depth += 1
            else:
                depth -= 1
                element.clear()
    except (ET.ParseError, LookupError, UnicodeError, ValueError) as exc:
        raise ValueError(f"malformed XML: {exc}") from exc
    return parsed


def _xml_priority(part: str) -> tuple[int, str]:
    if part == CONTENT_TYPES_PART:
        return 0, part
    if part == ROOT_RELS_PART:
        return 1, part
    if part == DOCUMENT_PART:
        return 2, part
    if part == DOCUMENT_RELS_PART:
        return 3, part
    if _is_family_part(part):
        return 4, part
    if posixpath.basename(part).casefold() in {"footnotes.xml", "endnotes.xml"}:
        return 5, part
    if part.casefold().endswith(".rels"):
        return 6, part
    return 7, part


def _normalize_content_type_part(part_name: str) -> tuple[str | None, str | None]:
    if _has_encoded_separator(part_name):
        return None, "percent-encoded separator in PartName"
    decoded = _decode_percent_layers(part_name)
    if "\\" in decoded:
        return None, "backslash in PartName"
    if not decoded.startswith("/"):
        return None, "Override PartName must begin with a package-root slash"
    body = decoded[1:]
    if not body:
        return None, "empty PartName"
    segments = body.split("/")
    if any(segment in {"", ".", ".."} for segment in segments):
        return None, "non-canonical PartName"
    canonical = posixpath.normpath(body)
    if canonical == ".." or canonical.startswith("../"):
        return None, "PartName escapes package root"
    return canonical, None


def _relationship_source(rel_part: str) -> str | None:
    if rel_part == "_rels/.rels":
        return ""
    marker = "/_rels/"
    if marker not in rel_part or not rel_part.endswith(".rels"):
        return None
    prefix, rel_name = rel_part.rsplit(marker, 1)
    source_name = rel_name[:-5]
    if not source_name:
        return None
    return f"{prefix}/{source_name}" if prefix else source_name


def _resolve_relationship_target(
    source: str, target: str
) -> tuple[str | None, str | None]:
    if "\\" in target:
        return None, "backslash in relationship target"
    if _has_encoded_separator(target):
        return None, "percent-encoded separator in relationship target"
    try:
        parsed = urlsplit(target)
    except ValueError as exc:
        return None, f"invalid relationship target URI: {exc}"
    if parsed.scheme or parsed.netloc:
        return None, "internal relationship target is an absolute URI"
    if parsed.query:
        return None, "internal relationship target contains a query"
    decoded = _decode_percent_layers(parsed.path)
    if "\\" in decoded:
        return None, "encoded backslash in relationship target"
    if not decoded:
        return None, "empty internal relationship target"
    if decoded.startswith("/"):
        candidate = decoded[1:]
    else:
        base = posixpath.dirname(source) if source else ""
        candidate = posixpath.join(base, decoded)
    canonical = posixpath.normpath(candidate)
    if canonical in {"", ".", ".."} or canonical.startswith("../"):
        return None, "relationship target escapes package root"
    return canonical, None


def _validate_content_types(
    result: dict[str, Any],
    records: list[dict[str, Any]],
    package_parts: set[str],
) -> tuple[list[dict[str, str]], dict[str, str], dict[str, str]]:
    family_records: list[dict[str, str]] = []
    override_types: dict[str, str] = {}
    default_types: dict[str, str] = {}
    seen_overrides: Counter[str] = Counter()
    seen_defaults: Counter[str] = Counter()

    for record in records:
        kind = record["kind"]
        content_type = record.get("content_type")
        if not content_type:
            _add_finding(
                result,
                "error",
                "content_type_missing_value",
                "Content type registration lacks ContentType.",
                part=CONTENT_TYPES_PART,
            )
            continue
        if kind == "Override":
            part_name = record.get("part_name")
            if not part_name:
                _add_finding(
                    result,
                    "error",
                    "content_type_missing_part_name",
                    "Override registration lacks PartName.",
                    part=CONTENT_TYPES_PART,
                )
                continue
            normalized, error = _normalize_content_type_part(part_name)
            if error or normalized is None:
                _add_finding(
                    result,
                    "error",
                    "unsafe_content_type_part_name",
                    error or "Invalid PartName.",
                    part=CONTENT_TYPES_PART,
                    details=part_name,
                )
                continue
            seen_overrides[normalized] += 1
            override_types.setdefault(normalized, content_type)
            if normalized not in package_parts:
                _add_finding(
                    result,
                    "issue",
                    "content_type_target_missing",
                    "Override registration targets a missing package part.",
                    part=CONTENT_TYPES_PART,
                    details=normalized,
                )
            if _is_family_part(normalized) or _has_family_token(content_type):
                family_records.append(
                    {
                        "kind": "Override",
                        "part": normalized,
                        "content_type": content_type,
                    }
                )
        else:
            extension = (record.get("extension") or "").lstrip(".").casefold()
            if not extension:
                _add_finding(
                    result,
                    "error",
                    "content_type_missing_extension",
                    "Default registration lacks Extension.",
                    part=CONTENT_TYPES_PART,
                )
                continue
            seen_defaults[extension] += 1
            default_types.setdefault(extension, content_type)
            if _has_family_token(content_type):
                family_records.append(
                    {
                        "kind": "Default",
                        "extension": extension,
                        "content_type": content_type,
                    }
                )

    duplicate_overrides = sorted(name for name, count in seen_overrides.items() if count > 1)
    if duplicate_overrides:
        _add_finding(
            result,
            "issue",
            "duplicate_content_type_override",
            "Multiple Override registrations name the same part.",
            part=CONTENT_TYPES_PART,
            count=len(duplicate_overrides),
            details=_limited_details(duplicate_overrides),
        )
    duplicate_defaults = sorted(name for name, count in seen_defaults.items() if count > 1)
    if duplicate_defaults:
        _add_finding(
            result,
            "issue",
            "duplicate_content_type_default",
            "Multiple Default registrations name the same extension.",
            part=CONTENT_TYPES_PART,
            count=len(duplicate_defaults),
            details=_limited_details(duplicate_defaults),
        )

    main_document_content_type = override_types.get(DOCUMENT_PART)
    if DOCUMENT_PART in package_parts and main_document_content_type is None:
        _add_finding(
            result,
            "error",
            "missing_main_document_content_type",
            "The main document must have an explicit content-type Override.",
            part=CONTENT_TYPES_PART,
            details=DOCUMENT_PART,
        )
    elif (
        main_document_content_type is not None
        and main_document_content_type not in MAIN_DOCUMENT_CONTENT_TYPES
    ):
        _add_finding(
            result,
            "error",
            "invalid_main_document_content_type",
            "The main document Override does not declare a DOCX main-document content type.",
            part=CONTENT_TYPES_PART,
            details={
                "part": DOCUMENT_PART,
                "content_type": main_document_content_type,
            },
        )

    uncovered_parts: list[str] = []
    for package_part in sorted(package_parts - {CONTENT_TYPES_PART}):
        if package_part in override_types:
            continue
        basename = posixpath.basename(package_part)
        extension = basename.rsplit(".", 1)[1].casefold() if "." in basename else ""
        if not extension or extension not in default_types:
            uncovered_parts.append(package_part)
    if uncovered_parts:
        _add_finding(
            result,
            "error",
            "package_parts_missing_content_type",
            "Package parts lack an applicable Override or Default content type.",
            part=CONTENT_TYPES_PART,
            count=len(uncovered_parts),
            details=_limited_details(uncovered_parts),
        )
    family_records.sort(
        key=lambda item: (
            item["kind"],
            item.get("part", ""),
            item.get("extension", ""),
            item["content_type"],
        )
    )
    return family_records, override_types, default_types


def _validate_relationships(
    result: dict[str, Any],
    relationships_by_part: dict[str, list[dict[str, Any]]],
    package_parts: set[str],
) -> tuple[list[dict[str, str]], dict[str, set[str]], set[str]]:
    family_relationships: list[dict[str, str]] = []
    adjacency: dict[str, set[str]] = defaultdict(set)
    relationship_targets: set[str] = set()
    external_relationships: list[dict[str, str]] = []
    missing_targets: list[dict[str, str]] = []

    for rel_part in sorted(relationships_by_part):
        source = _relationship_source(rel_part)
        if source is None:
            _add_finding(
                result,
                "issue",
                "invalid_relationship_part_name",
                "Relationship part cannot be mapped to a source part.",
                part=rel_part,
            )
            continue
        if source and source not in package_parts:
            _add_finding(
                result,
                "issue",
                "orphan_relationship_part",
                "Relationship part exists but its source part is missing.",
                part=rel_part,
                details=source,
            )

        records = relationships_by_part[rel_part]
        identifiers = Counter(record.get("id") for record in records if record.get("id"))
        duplicate_ids = sorted(value for value, count in identifiers.items() if count > 1)
        if duplicate_ids:
            _add_finding(
                result,
                "issue",
                "duplicate_relationship_id",
                "Relationship IDs must be unique within a relationship part.",
                part=rel_part,
                count=len(duplicate_ids),
                details=_limited_details(duplicate_ids),
            )

        for record in records:
            rel_id = record.get("id")
            rel_type = record.get("type")
            target = record.get("target")
            mode = (record.get("target_mode") or "Internal").casefold()
            if not rel_id or not rel_type or not target:
                _add_finding(
                    result,
                    "issue",
                    "incomplete_relationship",
                    "Relationship lacks Id, Type, or Target.",
                    part=rel_part,
                    details={
                        "id": rel_id,
                        "target": target,
                        "type": rel_type,
                    },
                )
                continue
            basic = {
                "source_relationship_part": rel_part,
                "id": rel_id,
                "type": rel_type,
                "target": target,
            }
            if mode == "external":
                external_relationships.append(basic)
                decoded_target = _decode_percent_layers(target)
                try:
                    external_scheme = urlsplit(decoded_target).scheme.casefold()
                except ValueError:
                    external_scheme = ""
                if external_scheme == "file":
                    _add_finding(
                        result,
                        "error",
                        "local_file_external_relationship",
                        "External relationships must not target a local file URI.",
                        part=rel_part,
                        details={"id": rel_id, "target": target},
                    )
                if _has_family_token(rel_type):
                    family_relationships.append({**basic, "mode": "External"})
                    _add_finding(
                        result,
                        "issue",
                        "external_comment_family_relationship",
                        "Comment-family relationship unexpectedly targets an external URI.",
                        part=rel_part,
                        details={"id": rel_id, "target": target},
                    )
                continue
            if mode != "internal":
                _add_finding(
                    result,
                    "issue",
                    "unknown_relationship_target_mode",
                    "Relationship TargetMode is neither Internal nor External.",
                    part=rel_part,
                    details={"id": rel_id, "target_mode": record.get("target_mode")},
                )
                continue
            resolved, error = _resolve_relationship_target(source, target)
            if error or resolved is None:
                _add_finding(
                    result,
                    "error",
                    "unsafe_relationship_target",
                    error or "Invalid internal relationship target.",
                    part=rel_part,
                    details={"id": rel_id, "target": target},
                )
                continue
            relationship_targets.add(resolved)
            is_family = _has_family_token(rel_type) or _is_family_part(resolved)
            if is_family:
                family_relationships.append(
                    {**basic, "mode": "Internal", "resolved_target": resolved}
                )
            if resolved not in package_parts:
                missing = {
                    "source_relationship_part": rel_part,
                    "id": rel_id,
                    "target": target,
                    "resolved_target": resolved,
                }
                missing_targets.append(missing)
                _add_finding(
                    result,
                    "issue",
                    "missing_relationship_target",
                    "Internal relationship target is absent from the package.",
                    part=rel_part,
                    details=missing,
                )
            else:
                adjacency[source].add(resolved)

    external_relationships.sort(
        key=lambda item: (
            item["source_relationship_part"],
            item["id"],
            item["target"],
        )
    )
    missing_targets.sort(
        key=lambda item: (
            item["source_relationship_part"],
            item["id"],
            item["resolved_target"],
        )
    )
    family_relationships.sort(
        key=lambda item: (
            item["source_relationship_part"],
            item["id"],
            item.get("resolved_target", item["target"]),
        )
    )
    result["metrics"]["external_relationships"] = external_relationships
    result["metrics"]["missing_relationship_targets"] = missing_targets
    if external_relationships:
        _add_finding(
            result,
            "info",
            "external_relationships_present",
            "Package contains external relationships; review their destinations and intent.",
            count=len(external_relationships),
        )
    return family_relationships, adjacency, relationship_targets


def _validate_package_entrypoint(
    result: dict[str, Any],
    relationships_by_part: dict[str, list[dict[str, Any]]],
) -> None:
    """Require one internal root relationship to the expected main document."""

    if ROOT_RELS_PART not in relationships_by_part:
        return

    office_document_relationships = [
        record
        for record in relationships_by_part[ROOT_RELS_PART]
        if record.get("type") in OFFICE_DOCUMENT_RELATIONSHIP_TYPES
    ]
    if not office_document_relationships:
        _add_finding(
            result,
            "error",
            "missing_office_document_relationship",
            "The package root relationships do not identify an officeDocument part.",
            part=ROOT_RELS_PART,
        )
        return
    if len(office_document_relationships) > 1:
        _add_finding(
            result,
            "error",
            "multiple_office_document_relationships",
            "The package root declares more than one officeDocument relationship.",
            part=ROOT_RELS_PART,
            count=len(office_document_relationships),
        )

    for record in office_document_relationships:
        rel_id = record.get("id")
        target = record.get("target")
        mode = (record.get("target_mode") or "Internal").casefold()
        if not rel_id or not target or mode != "internal":
            _add_finding(
                result,
                "error",
                "invalid_office_document_relationship",
                "The officeDocument relationship must be complete and internal.",
                part=ROOT_RELS_PART,
                details={
                    "id": rel_id,
                    "target": target,
                    "target_mode": record.get("target_mode"),
                },
            )
            continue
        resolved, error = _resolve_relationship_target("", target)
        if error or resolved != DOCUMENT_PART:
            _add_finding(
                result,
                "error",
                "invalid_office_document_target",
                "The officeDocument relationship must resolve to word/document.xml.",
                part=ROOT_RELS_PART,
                details={
                    "id": rel_id,
                    "target": target,
                    "resolved_target": resolved,
                    "error": error,
                },
            )


def _reachable_parts(adjacency: dict[str, set[str]], start: str) -> set[str]:
    reached: set[str] = {start}
    queue: deque[str] = deque([start])
    while queue:
        source = queue.popleft()
        for target in sorted(adjacency.get(source, set())):
            if target not in reached:
                reached.add(target)
                queue.append(target)
    return reached


def _content_type_is_specific_for_family(
    part: str, override_types: dict[str, str], default_types: dict[str, str]
) -> bool:
    if part in override_types:
        return _has_family_token(override_types[part])
    extension = posixpath.splitext(part)[1].lstrip(".").casefold()
    return _has_family_token(default_types.get(extension))


def _validate_comment_closure(
    result: dict[str, Any],
    package_parts: set[str],
    family_content_types: list[dict[str, str]],
    override_types: dict[str, str],
    default_types: dict[str, str],
    family_relationships: list[dict[str, str]],
    adjacency: dict[str, set[str]],
    relationship_targets: set[str],
    marker_ids: dict[str, Counter[str]],
    marker_missing_ids: Counter[str],
    definition_ids: Counter[str],
    definition_missing_ids: int,
) -> None:
    family_parts = sorted(part for part in package_parts if _is_family_part(part))
    result["metrics"]["comment_family_parts"] = family_parts
    result["metrics"]["comment_family_relationships"] = family_relationships
    result["metrics"]["comment_family_content_types"] = family_content_types
    result["metrics"]["comment_definitions"] = sum(definition_ids.values()) + definition_missing_ids

    marker_total = sum(sum(counter.values()) for counter in marker_ids.values()) + sum(
        marker_missing_ids.values()
    )
    for name in COMMENT_MARKER_NAMES:
        result["metrics"]["comment_markers"][name] = sum(marker_ids[name].values()) + marker_missing_ids[name]

    for part in family_parts:
        if not _content_type_is_specific_for_family(part, override_types, default_types):
            _add_finding(
                result,
                "issue",
                "comment_family_part_missing_content_type",
                "Comment-family part lacks a matching family-specific content type.",
                part=part,
            )
        if part not in relationship_targets:
            _add_finding(
                result,
                "issue",
                "orphan_comment_family_part",
                "Comment-family part is not the target of any internal relationship.",
                part=part,
            )

    if DOCUMENT_PART in package_parts:
        reachable = _reachable_parts(adjacency, DOCUMENT_PART)
        unreachable = sorted(part for part in family_parts if part not in reachable)
        if unreachable:
            _add_finding(
                result,
                "issue",
                "comment_family_part_not_reachable",
                "Comment-family parts are not reachable from the main document relationship graph.",
                count=len(unreachable),
                details=_limited_details(unreachable),
            )

    if marker_total == 0:
        if family_parts:
            _add_finding(
                result,
                "issue",
                "residual_comment_family_parts",
                "Comment-family parts remain although no visible comment markers were found.",
                count=len(family_parts),
                details=_limited_details(family_parts),
            )
        if family_relationships:
            _add_finding(
                result,
                "issue",
                "residual_comment_relationships",
                "Comment-family relationships remain although no visible comment markers were found.",
                count=len(family_relationships),
            )
        if family_content_types:
            _add_finding(
                result,
                "issue",
                "residual_comment_content_types",
                "Comment-family content-type registrations remain although no visible comment markers were found.",
                count=len(family_content_types),
            )
        return

    _add_finding(
        result,
        "info",
        "visible_comment_markup_present",
        "Visible comment anchors or reference markers are present.",
        count=marker_total,
    )
    base_parts = sorted(part for part in family_parts if _is_base_comments_part(part))
    if not base_parts:
        _add_finding(
            result,
            "issue",
            "comment_markers_without_comments_part",
            "Visible comment markers exist but no base comments.xml part is present.",
        )

    if marker_missing_ids:
        _add_finding(
            result,
            "issue",
            "comment_marker_missing_id",
            "Comment markers without an ID cannot be closed against comment definitions.",
            count=sum(marker_missing_ids.values()),
            details=dict(sorted(marker_missing_ids.items())),
        )
    if definition_missing_ids:
        _add_finding(
            result,
            "issue",
            "comment_definition_missing_id",
            "Comment definitions without an ID cannot be matched to visible markers.",
            count=definition_missing_ids,
        )
    duplicate_definitions = sorted(
        comment_id for comment_id, count in definition_ids.items() if count > 1
    )
    if duplicate_definitions:
        _add_finding(
            result,
            "issue",
            "duplicate_comment_definition_id",
            "Multiple base comment definitions use the same ID.",
            count=len(duplicate_definitions),
            details=_limited_details(duplicate_definitions),
        )

    all_marker_ids = set().union(*(set(counter) for counter in marker_ids.values()))
    unresolved = sorted(all_marker_ids - set(definition_ids))
    if unresolved:
        _add_finding(
            result,
            "issue",
            "comment_marker_without_definition",
            "Visible comment marker IDs have no base comment definition.",
            count=len(unresolved),
            details=_limited_details(unresolved),
        )
    unreferenced_definitions = sorted(
        set(definition_ids) - set(marker_ids["commentReference"])
    )
    if unreferenced_definitions:
        _add_finding(
            result,
            "issue",
            "comment_definition_without_reference",
            "Base comment definitions have no visible commentReference marker.",
            count=len(unreferenced_definitions),
            details=_limited_details(unreferenced_definitions),
        )

    imbalanced = sorted(
        comment_id
        for comment_id in set(marker_ids["commentRangeStart"]) | set(marker_ids["commentRangeEnd"])
        if marker_ids["commentRangeStart"][comment_id]
        != marker_ids["commentRangeEnd"][comment_id]
    )
    if imbalanced:
        _add_finding(
            result,
            "issue",
            "comment_range_imbalance",
            "Comment range start and end marker counts do not match by ID.",
            count=len(imbalanced),
            details=_limited_details(imbalanced),
        )


def _add_feature_findings(result: dict[str, Any]) -> None:
    metrics = result["metrics"]
    tracked_total = sum(metrics["tracked_changes"].values())
    if tracked_total:
        _add_finding(
            result,
            "info",
            "tracked_changes_present",
            "Tracked-change containers are present; accept or reject them intentionally.",
            count=tracked_total,
            details=metrics["tracked_changes"],
        )
    field_total = sum(metrics["field_codes"].values())
    if field_total:
        _add_finding(
            result,
            "info",
            "field_codes_present",
            "Field-code structures are present and may require preservation during edits.",
            count=field_total,
            details=metrics["field_codes"],
        )
    equation_total = sum(metrics["equations"].values())
    if equation_total:
        _add_finding(
            result,
            "info",
            "equations_present",
            "OMML equation structures are present and must not be flattened to plain text.",
            count=equation_total,
            details=metrics["equations"],
        )
    note_count = metrics["footnotes"]["elements"] + metrics["endnotes"]["elements"]
    note_parts = len(metrics["footnotes"]["parts"]) + len(metrics["endnotes"]["parts"])
    if note_count or note_parts:
        _add_finding(
            result,
            "info",
            "footnotes_or_endnotes_present",
            "Footnote or endnote structures are present.",
            count=note_count,
            details={
                "endnotes": metrics["endnotes"],
                "footnotes": metrics["footnotes"],
            },
        )


def audit_docx(path_value: str | os.PathLike[str]) -> dict[str, Any]:
    """Audit one DOCX path and return a deterministic JSON-serializable result."""

    path = Path(path_value)
    result = _new_result(path)
    if path.suffix.casefold() != ".docx":
        _add_finding(
            result,
            "error",
            "not_docx_path",
            "Input path must have a .docx extension.",
        )
        return _finish_result(result)
    if not path.is_file():
        _add_finding(
            result,
            "error",
            "input_not_found",
            "Input DOCX does not exist or is not a regular file.",
        )
        return _finish_result(result)

    try:
        zf = zipfile.ZipFile(path, "r")
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, EOFError) as exc:
        _add_finding(
            result,
            "error",
            "invalid_or_unreadable_zip",
            f"DOCX package cannot be opened as a valid ZIP: {exc}",
        )
        return _finish_result(result)

    with zf:
        try:
            infos = zf.infolist()
        except (zipfile.BadZipFile, OSError, EOFError) as exc:
            _add_finding(
                result,
                "error",
                "unreadable_zip_directory",
                f"ZIP central directory cannot be read: {exc}",
            )
            return _finish_result(result)

        package = result["package"]
        package["entries"] = len(infos)
        package["directory_entries"] = sum(info.is_dir() for info in infos)
        package["file_entries"] = len(infos) - package["directory_entries"]
        package["total_uncompressed_bytes"] = sum(info.file_size for info in infos)

        canonical_groups: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        all_canonical_groups: dict[str, list[zipfile.ZipInfo]] = defaultdict(list)
        case_groups: dict[str, set[str]] = defaultdict(set)
        unsafe_entries: list[dict[str, Any]] = []
        encrypted_entries: list[str] = []
        symlink_entries: list[str] = []
        excessive_ratio_entries: list[str] = []
        excessive_member_entries: list[str] = []

        for info in infos:
            canonical, reasons = _canonical_zip_name(info.filename)
            if _is_symlink(info):
                symlink_entries.append(info.filename)
            if info.flag_bits & 0x1:
                encrypted_entries.append(info.filename)
            if info.file_size > MAX_MEMBER_UNCOMPRESSED:
                excessive_member_entries.append(info.filename)
            if (
                info.file_size > 1024 * 1024
                and info.compress_size >= 0
                and info.file_size / max(info.compress_size, 1) > MAX_COMPRESSION_RATIO
            ):
                excessive_ratio_entries.append(info.filename)
            if reasons:
                unsafe_entries.append({"name": info.filename, "reasons": reasons})
                continue
            all_canonical_groups[canonical].append(info)
            case_groups[canonical.casefold()].add(canonical)
            if not info.is_dir():
                canonical_groups[canonical].append(info)

        unsafe_entries.sort(key=lambda item: item["name"])
        package["unsafe_entries"] = unsafe_entries
        duplicate_entries = sorted(
            name for name, group in all_canonical_groups.items() if len(group) > 1
        )
        case_collisions = sorted(
            sorted(names) for names in case_groups.values() if len(names) > 1
        )
        package["duplicate_entries"] = duplicate_entries
        package["case_collisions"] = case_collisions

        if unsafe_entries:
            _add_finding(
                result,
                "error",
                "unsafe_zip_path",
                "Package contains non-canonical or path-escaping member names; deep audit was rejected.",
                count=len(unsafe_entries),
                details=_limited_details(unsafe_entries),
            )
        if duplicate_entries:
            _add_finding(
                result,
                "issue",
                "duplicate_zip_entry",
                "Package contains duplicate or normalization-colliding ZIP entries; deep audit was rejected.",
                count=len(duplicate_entries),
                details=_limited_details(duplicate_entries),
            )
        if case_collisions:
            _add_finding(
                result,
                "issue",
                "case_colliding_zip_entry",
                "Package member names collide under case-insensitive comparison; deep audit was rejected.",
                count=len(case_collisions),
                details=_limited_details(case_collisions),
            )
        if symlink_entries:
            _add_finding(
                result,
                "issue",
                "zip_symlink_entry",
                "DOCX package contains symbolic-link entries; deep audit was rejected.",
                count=len(symlink_entries),
                details=_limited_details(sorted(symlink_entries)),
            )
        if encrypted_entries:
            _add_finding(
                result,
                "error",
                "encrypted_zip_entry",
                "Encrypted package entries cannot be audited without a password.",
                count=len(encrypted_entries),
                details=_limited_details(sorted(encrypted_entries)),
            )
        if len(infos) > MAX_ENTRIES:
            _add_finding(
                result,
                "issue",
                "zip_entry_limit_exceeded",
                f"Package exceeds the safe entry limit of {MAX_ENTRIES}.",
                count=len(infos),
            )
        if package["total_uncompressed_bytes"] > MAX_TOTAL_UNCOMPRESSED:
            _add_finding(
                result,
                "issue",
                "zip_uncompressed_size_limit_exceeded",
                f"Package exceeds the safe expanded-size limit of {MAX_TOTAL_UNCOMPRESSED} bytes.",
                count=package["total_uncompressed_bytes"],
            )
        if excessive_member_entries:
            _add_finding(
                result,
                "issue",
                "zip_member_size_limit_exceeded",
                f"Package members exceed the safe per-member limit of {MAX_MEMBER_UNCOMPRESSED} bytes.",
                count=len(excessive_member_entries),
                details=_limited_details(sorted(excessive_member_entries)),
            )
        if excessive_ratio_entries:
            _add_finding(
                result,
                "issue",
                "suspicious_compression_ratio",
                "Package members exceed the safe compression-ratio limit.",
                count=len(excessive_ratio_entries),
                details=_limited_details(sorted(excessive_ratio_entries)),
            )

        reject_codes = {
            "unsafe_zip_path",
            "duplicate_zip_entry",
            "case_colliding_zip_entry",
            "zip_symlink_entry",
            "encrypted_zip_entry",
            "zip_entry_limit_exceeded",
            "zip_uncompressed_size_limit_exceeded",
            "zip_member_size_limit_exceeded",
            "suspicious_compression_ratio",
        }
        if any(finding["code"] in reject_codes for finding in result["findings"]):
            package["rejected_for_safe_audit"] = True
            _add_finding(
                result,
                "info",
                "deep_audit_skipped",
                "Semantic XML audit was skipped because the package failed safe-open checks.",
            )
            return _finish_result(result)

        try:
            corrupt_member = zf.testzip()
        except (
            zipfile.BadZipFile,
            RuntimeError,
            OSError,
            EOFError,
            NotImplementedError,
            zlib.error,
        ) as exc:
            _add_finding(
                result,
                "error",
                "zip_integrity_check_failed",
                f"ZIP member integrity could not be verified: {exc}",
            )
            return _finish_result(result)
        if corrupt_member is not None:
            _add_finding(
                result,
                "error",
                "corrupt_zip_member",
                "ZIP CRC check reported a corrupt package member.",
                part=corrupt_member,
            )
            return _finish_result(result)

        entry_map = {name: group[0] for name, group in canonical_groups.items()}
        package_parts = set(entry_map)
        if CONTENT_TYPES_PART not in package_parts:
            _add_finding(
                result,
                "error",
                "missing_content_types_part",
                "Required [Content_Types].xml package part is missing.",
                part=CONTENT_TYPES_PART,
            )
        if ROOT_RELS_PART not in package_parts:
            _add_finding(
                result,
                "error",
                "missing_package_relationships_part",
                "Required package-root relationship part is missing.",
                part=ROOT_RELS_PART,
            )
        if DOCUMENT_PART not in package_parts:
            _add_finding(
                result,
                "error",
                "missing_main_document_part",
                "Expected main Word document part is missing.",
                part=DOCUMENT_PART,
            )
        if DOCUMENT_RELS_PART not in package_parts:
            _add_finding(
                result,
                "info",
                "document_relationships_part_absent",
                "Main document relationship part is absent; this can be valid only when the document has no relationships.",
                part=DOCUMENT_RELS_PART,
            )

        xml_parts = sorted(
            (
                part
                for part in package_parts
                if part == CONTENT_TYPES_PART
                or part.casefold().endswith(".xml")
                or part.casefold().endswith(".rels")
            ),
            key=_xml_priority,
        )
        parsed_parts: list[str] = []
        skipped_parts: list[str] = []
        xml_bytes_read = 0
        tracked: Counter[str] = Counter()
        fields: Counter[str] = Counter()
        equations: Counter[str] = Counter()
        marker_ids = {name: Counter() for name in COMMENT_MARKER_NAMES}
        marker_missing_ids: Counter[str] = Counter()
        definition_ids: Counter[str] = Counter()
        definition_missing_ids = 0
        footnote_elements = 0
        endnote_elements = 0
        content_type_records: list[dict[str, Any]] = []
        relationships_by_part: dict[str, list[dict[str, Any]]] = {}

        for part in xml_parts:
            info = entry_map[part]
            if info.file_size > MAX_XML_MEMBER or xml_bytes_read + info.file_size > MAX_XML_TOTAL:
                skipped_parts.append(part)
                _add_finding(
                    result,
                    "issue",
                    "xml_audit_size_limit_exceeded",
                    "XML part was not parsed because the safe XML audit limit would be exceeded.",
                    part=part,
                    count=info.file_size,
                )
                continue
            try:
                data = _read_member(zf, info)
            except AuditReadError as exc:
                _add_finding(
                    result,
                    "error",
                    "xml_member_read_error",
                    f"XML package member could not be read: {exc}",
                    part=part,
                )
                skipped_parts.append(part)
                continue
            xml_bytes_read += len(data)
            try:
                parsed = _parse_xml_part(part, data)
            except ValueError as exc:
                _add_finding(
                    result,
                    "error",
                    "invalid_xml_part",
                    str(exc),
                    part=part,
                )
                skipped_parts.append(part)
                continue

            parsed_parts.append(part)
            tracked.update(parsed["tracked"])
            fields.update(parsed["fields"])
            equations.update(parsed["equations"])
            for name in COMMENT_MARKER_NAMES:
                marker_ids[name].update(parsed["markers"][name])
            marker_missing_ids.update(parsed["marker_missing_ids"])
            definition_ids.update(parsed["definition_ids"])
            definition_missing_ids += parsed["definition_missing_ids"]
            footnote_elements += parsed["footnotes"]
            endnote_elements += parsed["endnotes"]
            if part == CONTENT_TYPES_PART:
                if (
                    parsed["root"] != "Types"
                    or parsed["root_namespace"] != CONTENT_TYPES_NAMESPACE
                ):
                    _add_finding(
                        result,
                        "error",
                        "invalid_content_types_root",
                        "[Content_Types].xml must use the OPC content-types Types root.",
                        part=part,
                        details={
                            "local_name": parsed["root"],
                            "namespace": parsed["root_namespace"],
                        },
                    )
                content_type_records = parsed["content_types"]
            if part == DOCUMENT_PART:
                if (
                    parsed["root"] != "document"
                    or parsed["root_namespace"] not in WORD_NAMESPACES
                ):
                    _add_finding(
                        result,
                        "error",
                        "invalid_main_document_root",
                        "word/document.xml must use a recognized WordprocessingML document root.",
                        part=part,
                        details={
                            "local_name": parsed["root"],
                            "namespace": parsed["root_namespace"],
                        },
                    )
                if parsed["document_body_count"] != 1:
                    _add_finding(
                        result,
                        "error",
                        "invalid_main_document_body",
                        "word/document.xml must contain exactly one direct WordprocessingML body.",
                        part=part,
                        count=parsed["document_body_count"],
                    )
            if part.casefold().endswith(".rels"):
                if (
                    parsed["root"] != "Relationships"
                    or parsed["root_namespace"] != RELATIONSHIPS_NAMESPACE
                ):
                    _add_finding(
                        result,
                        "error",
                        "invalid_relationships_root",
                        "Relationship parts must use the OPC Relationships root.",
                        part=part,
                        details={
                            "local_name": parsed["root"],
                            "namespace": parsed["root_namespace"],
                        },
                    )
                relationships_by_part[part] = parsed["relationships"]

        result["metrics"]["parsed_xml_parts"] = sorted(parsed_parts)
        result["metrics"]["skipped_xml_parts"] = sorted(skipped_parts)
        result["metrics"]["tracked_changes"] = {
            name: tracked[name] for name in TRACKED_CHANGE_NAMES
        }
        result["metrics"]["field_codes"] = {
            name: fields[name] for name in FIELD_CODE_NAMES
        }
        result["metrics"]["equations"] = {
            name: equations[name] for name in ("oMath", "oMathPara")
        }
        result["metrics"]["footnotes"] = {
            "parts": sorted(
                part
                for part in package_parts
                if posixpath.basename(part).casefold() == "footnotes.xml"
            ),
            "elements": footnote_elements,
        }
        result["metrics"]["endnotes"] = {
            "parts": sorted(
                part
                for part in package_parts
                if posixpath.basename(part).casefold() == "endnotes.xml"
            ),
            "elements": endnote_elements,
        }

        family_content_types, override_types, default_types = _validate_content_types(
            result, content_type_records, package_parts
        )
        family_relationships, adjacency, relationship_targets = _validate_relationships(
            result, relationships_by_part, package_parts
        )
        _validate_package_entrypoint(result, relationships_by_part)
        _validate_comment_closure(
            result,
            package_parts,
            family_content_types,
            override_types,
            default_types,
            family_relationships,
            adjacency,
            relationship_targets,
            marker_ids,
            marker_missing_ids,
            definition_ids,
            definition_missing_ids,
        )
        _add_feature_findings(result)
        package["deep_audit_complete"] = not skipped_parts and not any(
            finding["severity"] == "error" for finding in result["findings"]
        )
        return _finish_result(result)


def audit_paths(paths: Iterable[str | os.PathLike[str]]) -> dict[str, Any]:
    files = [audit_docx(path) for path in paths]
    errors = sum(item["status"] == "read_error" for item in files)
    issues = sum(item["status"] == "issues" for item in files)
    exit_code = 2 if errors else 1 if issues else 0
    return {
        "tool": "audit_docx_package",
        "schema_version": SCHEMA_VERSION,
        "scope": (
            "Read-only package-structure audit; this does not verify rendered "
            "appearance, pagination, or semantic correctness."
        ),
        "files": files,
        "summary": {
            "files": len(files),
            "ok": sum(item["status"] == "ok" for item in files),
            "with_issues": issues,
            "read_errors": errors,
        },
        "exit_code": exit_code,
    }


def _format_text(report: dict[str, Any]) -> str:
    lines: list[str] = []
    for item in report["files"]:
        lines.append(f"FILE {item['path']}")
        lines.append(f"STATUS {item['status']}")
        summary = item["summary"]
        lines.append(
            "SUMMARY "
            f"errors={summary['errors']} issues={summary['issues']} info={summary['info']}"
        )
        for finding in item["findings"]:
            label = finding["severity"].upper()
            location = f" part={finding['part']}" if "part" in finding else ""
            count = f" count={finding['count']}" if "count" in finding else ""
            lines.append(
                f"[{label}] {finding['code']}{location}{count}: {finding['message']}"
            )
            if "details" in finding:
                lines.append(
                    "  details="
                    + json.dumps(
                        finding["details"],
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
        lines.append(f"SCOPE {item['scope']}")
    summary = report["summary"]
    lines.append(
        "OVERALL "
        f"files={summary['files']} ok={summary['ok']} "
        f"with_issues={summary['with_issues']} read_errors={summary['read_errors']} "
        f"exit_code={report['exit_code']}"
    )
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit of DOCX ZIP/OpenXML structure. The audit does not "
            "verify visual rendering."
        )
    )
    parser.add_argument(
        "docx",
        nargs="+",
        metavar="DOCX",
        help="one or more .docx files to audit",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_utf8_stdio()
    args = _build_parser().parse_args(argv)
    report = audit_paths(args.docx)
    if args.output_format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_format_text(report))
    return int(report["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
