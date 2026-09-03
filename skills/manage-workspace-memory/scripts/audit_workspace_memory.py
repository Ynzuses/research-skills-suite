#!/usr/bin/env python3
"""Read-only integrity audit for a file-based workspace memory system.

The auditor intentionally uses only the Python standard library.  It reads
Markdown as strict UTF-8, never follows directory symlinks, and never writes,
moves, repairs, or deletes workspace content.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator, Sequence
from urllib.parse import unquote_to_bytes


ENTRY_POINT_NAMES = {
    "agents.md",
    "claude.md",
    "readme.md",
    "workspace_rules.md",
}

MARKDOWN_SUFFIXES = {".md", ".markdown", ".mdown"}

# These directories are implementation/cache internals rather than workspace
# memory.  The list is deliberately short and predictable.
IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}

EXPLICIT_ID_LABELS = {
    "area id",
    "artifact id",
    "asset id",
    "decision id",
    "design id",
    "edge id",
    "input id",
    "output id",
    "record id",
    "stable id",
    "区域 id",
    "区域id",
    "产物 id",
    "产物id",
    "决策 id",
    "决策id",
    "稳定 id",
    "稳定id",
    "设计 id",
    "设计id",
    "资产 id",
    "资产id",
    "输入 id",
    "输入id",
    "输出 id",
    "输出id",
    "记录 id",
    "记录id",
    "边 id",
    "边id",
}

DEFINITION_DOCUMENT_RE = re.compile(
    r"(?ix)"
    r"(?:\bstable[\s_-]*design\b|\basset[\s_-]*index\b|"
    r"\b(?:canonical|authority|identity|decision|id)[\s_-]*(?:registry|register|catalog)\b|"
    r"稳定设计|资产索引|(?:权威|身份|决策|标识|id)(?:登记|注册表|目录))"
)

DEFINITION_LABEL_RE = re.compile(
    r"(?ix)"
    r"(?:\b(?:authoritative|canonical|defined|definition)\b|"
    r"权威|规范|定义)"
)

REFERENCE_LABEL_RE = re.compile(
    r"(?ix)"
    r"(?:\b(?:reference|referenced|upstream|downstream|parent|source|dependency)\b|"
    r"引用|参照|上游|下游|父级|来源|依赖)"
)

HTML_TAG_NAMES = {
    "a",
    "abbr",
    "address",
    "article",
    "aside",
    "audio",
    "b",
    "blockquote",
    "body",
    "br",
    "button",
    "caption",
    "cite",
    "code",
    "col",
    "colgroup",
    "dd",
    "del",
    "details",
    "dfn",
    "div",
    "dl",
    "dt",
    "em",
    "figcaption",
    "figure",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "head",
    "header",
    "hr",
    "html",
    "i",
    "img",
    "input",
    "ins",
    "kbd",
    "label",
    "li",
    "main",
    "mark",
    "nav",
    "ol",
    "option",
    "p",
    "picture",
    "pre",
    "q",
    "s",
    "samp",
    "section",
    "select",
    "small",
    "source",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "textarea",
    "tfoot",
    "th",
    "thead",
    "time",
    "title",
    "tr",
    "u",
    "ul",
    "var",
    "video",
}

# A bare form such as ``<link>`` is much more likely to be one of this
# Skill's template tokens than useful inline HTML.  Real HTML forms normally
# carry attributes (for example ``<link rel=...>``), which are excluded below.
AMBIGUOUS_PLACEHOLDER_TAGS = {"input", "link", "source", "time"}

PLACEHOLDER_TERMS = {
    "acceptance",
    "action",
    "active",
    "area",
    "asset",
    "authoritative",
    "authority",
    "blocker",
    "boundaries",
    "condition",
    "convention",
    "coordinate",
    "criterion",
    "data",
    "date",
    "decision",
    "definition",
    "dependency",
    "evidence",
    "fact",
    "file",
    "follow",
    "hash",
    "id",
    "input",
    "link",
    "location",
    "method",
    "name",
    "none",
    "objective",
    "origin",
    "output",
    "owner",
    "path",
    "pattern",
    "policy",
    "privacy",
    "purpose",
    "relative",
    "result",
    "role",
    "root",
    "scope",
    "source",
    "stable",
    "state",
    "status",
    "task",
    "test",
    "time",
    "timezone",
    "trigger",
    "unknown",
    "verification",
    "version",
    "yyyy",
    "占位符",
    "作用域",
    "日期",
    "路径",
    "链接",
    "待填写",
    "待补充",
}

ANGLE_TOKEN_RE = re.compile(r"<([^<>\r\n]{1,160})>")
BRACE_TOKEN_RE = re.compile(r"\{\{[^{}\r\n]{1,160}\}\}")
REFERENCE_LINK_RE = re.compile(
    r"^\s{0,3}\[(?P<label>[^\]\r\n]+)\]:\s*"
    r"(?P<destination><[^>\r\n]*>|\S+)"
)
FENCE_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
TABLE_SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:")
URI_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

FROZEN_TRIGGER_RE = re.compile(
    r"(?ix)"
    r"(?:\bsubmitted\b|\bformally\s+circulated\b|"
    r"\b(?:frozen|freeze)\b.{0,50}\b(?:baseline|artifact|document|copy|release|submission|deliverable)\b|"
    r"\b(?:baseline|artifact|document|copy|release|submission|deliverable)\b.{0,50}\b(?:frozen|freeze)\b|"
    r"已提交|正式提交|正式流转|"
    r"(?:冻结|封存).{0,24}(?:基线|版本|文档|稿件|产物|文件|交付)|"
    r"(?:基线|版本|文档|稿件|产物|文件|交付).{0,24}(?:冻结|封存))"
)
FROZEN_NEGATION_RE = re.compile(
    r"(?i)\b(?:not|never)\s+(?:submitted|frozen)\b|"
    r"未提交|尚未提交|待提交|未冻结|尚未冻结|待冻结|计划冻结|不冻结"
)
ARTIFACT_CLUE_RE = re.compile(
    r"(?ix)"
    r"(?:\b(?:stable|artifact|asset|baseline|document)\s*id\b|"
    r"(?:稳定|产物|资产|基线|文档)\s*id|"
    r"[^\s<>\[\]()]+\.(?:docx?|pdf|md|markdown|txt|csv|tsv|xlsx?|pptx?|"
    r"zip|tar|gz|bz2|xz|json|yaml|yml))"
)
IMMUTABLE_CLUE_RE = re.compile(
    r"(?ix)"
    r"(?:sha(?:-?256|-?512)?|checksum|content\s+hash|哈希|校验和|"
    r"\b(?:version|revision|commit|tag)\s*[:=#]?\s*[A-Za-z0-9._/-]+|"
    r"(?:版本|修订|提交哈希|标签)\s*[:：=#]?\s*\S+|"
    r"\b[0-9a-f]{12,128}\b|"
    r"(?:^|[/_.-])v?\d+(?:\.\d+)+(?:$|[/_.-]))"
)


STATUS_FIELD_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "objective/current stage": (
        re.compile(r"\b(?:objective|current goal|project goal|current stage)\b", re.I),
        re.compile(r"当前目标|项目目标|本阶段目标|当前阶段"),
    ),
    "last verified": (
        re.compile(r"\b(?:last verified|last verification|verified on)\b", re.I),
        re.compile(r"最后核验|最近核验|上次核验|核验时间|最后验证|最近验证|验证时间|本轮验证状态"),
    ),
    "verification method": (
        re.compile(r"\bverification (?:method|basis)\b", re.I),
        re.compile(r"核验方法|核验方式|核验依据|验证方法|验证方式|验证依据"),
    ),
    "parent memory route": (
        re.compile(r"\b(?:parent memory route|memory route|memory entry|status route)\b", re.I),
        re.compile(r"父级记忆(?:路由|入口)|记忆(?:路由|入口)|状态路由"),
    ),
    "verified/current state": (
        re.compile(r"\b(?:verified state|current state|current progress)\b", re.I),
        re.compile(r"已核验状态|当前状态|当前进展|本轮已完成|已完成"),
    ),
    "first/next action": (
        re.compile(r"\b(?:first safe next action|first next action|next action|next step)\b", re.I),
        re.compile(r"下一(?:阶段|会话)?第一动作|第一安全动作|下一动作|下一步"),
    ),
    "blockers/decisions": (
        re.compile(r"\b(?:blockers?|decisions? needed|blocked by)\b", re.I),
        re.compile(r"阻塞|待确认|待决策|决策门"),
    ),
}


class WorkspaceReadError(RuntimeError):
    """A deterministic usage or filesystem/decoding failure."""


@dataclass(frozen=True)
class Document:
    path: Path
    relative_path: str
    text: str


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    line: int | None
    message: str


@dataclass(frozen=True)
class AuditResult:
    root: str
    markdown_file_count: int
    entry_points: tuple[str, ...]
    status_files: tuple[str, ...]
    three_hop_routes: tuple[str, ...]
    issues: tuple[Issue, ...]


def _configure_utf8_streams() -> None:
    """Keep Chinese paths/messages intact even in legacy Windows consoles."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")


def _stable_text_key(value: str) -> tuple[str, str]:
    return value.casefold(), value


def _issue_key(issue: Issue) -> tuple[str, str, int, str, str]:
    return (
        issue.path.casefold(),
        issue.path,
        issue.line if issue.line is not None else 0,
        issue.code,
        issue.message,
    )


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _to_relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _read_utf8_strict(path: Path) -> str:
    try:
        # utf-8-sig accepts an optional BOM but otherwise remains strict UTF-8.
        return path.read_text(encoding="utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        raise WorkspaceReadError(
            f"cannot decode as strict UTF-8: {path} (byte {exc.start})"
        ) from exc
    except OSError as exc:
        raise WorkspaceReadError(f"cannot read {path}: {exc}") from exc


def _collect_documents(root: Path) -> tuple[list[Document], list[Issue]]:
    candidates: list[Path] = []

    def on_walk_error(error: OSError) -> None:
        location = error.filename or str(root)
        raise WorkspaceReadError(f"cannot enumerate {location}: {error}") from error

    try:
        for directory, directory_names, file_names in os.walk(
            root, topdown=True, onerror=on_walk_error, followlinks=False
        ):
            directory_names[:] = sorted(
                (
                    name
                    for name in directory_names
                    if name.casefold() not in IGNORED_DIRECTORY_NAMES
                    and not Path(directory, name).is_symlink()
                ),
                key=_stable_text_key,
            )
            for name in sorted(file_names, key=_stable_text_key):
                candidate = Path(directory, name)
                if candidate.suffix.casefold() in MARKDOWN_SUFFIXES:
                    candidates.append(candidate)
    except OSError as exc:
        raise WorkspaceReadError(f"cannot enumerate {root}: {exc}") from exc

    candidates.sort(
        key=lambda path: _stable_text_key(_to_relative_posix(path, root))
    )
    documents: list[Document] = []
    issues: list[Issue] = []
    for path in candidates:
        relative_path = _to_relative_posix(path, root)
        try:
            resolved = path.resolve(strict=False)
        except OSError as exc:
            raise WorkspaceReadError(f"cannot resolve {path}: {exc}") from exc
        if not _is_within(resolved, root):
            issues.append(
                Issue(
                    code="MARKDOWN_FILE_ESCAPE",
                    path=relative_path,
                    line=None,
                    message="Markdown file is a link to a location outside the audit root.",
                )
            )
            continue
        documents.append(
            Document(
                path=path,
                relative_path=relative_path,
                text=_read_utf8_strict(path),
            )
        )
    return documents, issues


def _is_placeholder_body(body: str) -> bool:
    value = body.strip()
    if not value or value.startswith(("/", "!", "?")):
        return False
    lowered = value.casefold()
    if "://" in lowered or lowered.startswith(("mailto:", "doi:")):
        return False
    if "=" in value:
        return False
    if re.search(r"\.[A-Za-z0-9]{1,12}(?:[?#].*)?$", value):
        # ``<docs/my file.md>`` is Markdown's angle-bracket destination form,
        # not a template token.
        return False
    words = set(re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", lowered))
    first_name_match = re.match(r"[A-Za-z][A-Za-z0-9-]*", lowered)
    if first_name_match and first_name_match.group(0) in HTML_TAG_NAMES:
        first_name = first_name_match.group(0)
        other_words = words - {first_name}
        if (
            first_name not in AMBIGUOUS_PLACEHOLDER_TAGS
            and not (other_words & PLACEHOLDER_TERMS)
        ):
            return False
    if words & PLACEHOLDER_TERMS:
        return True
    return bool(re.fullmatch(r"(?:TODO|TBD|PLACEHOLDER)(?:[-_ ][A-Z0-9]+)*", value))


def _iter_placeholder_tokens(line: str) -> Iterator[str]:
    for match in ANGLE_TOKEN_RE.finditer(line):
        token = match.group(0)
        if _is_placeholder_body(match.group(1)):
            yield token
    for match in BRACE_TOKEN_RE.finditer(line):
        yield match.group(0)


def _check_placeholders(documents: Sequence[Document]) -> list[Issue]:
    issues: list[Issue] = []
    for document in documents:
        # Templates shown as Markdown examples are inert documentation, not
        # unresolved workspace state.  Use the same code/comment masking as
        # the link and stable-ID scanners so fenced and inline code cannot
        # create false positives while prose placeholders remain visible.
        for line_number, line in enumerate(
            _masked_markdown_lines(document.text), start=1
        ):
            seen_on_line: set[str] = set()
            for token in _iter_placeholder_tokens(line):
                if token in seen_on_line:
                    continue
                seen_on_line.add(token)
                issues.append(
                    Issue(
                        code="UNRESOLVED_TEMPLATE_PLACEHOLDER",
                        path=document.relative_path,
                        line=line_number,
                        message=f"Unresolved template placeholder: {token!r}.",
                    )
                )
    return issues


def _mask_html_comments(line: str, comment_open: bool) -> tuple[str, bool]:
    characters = list(line)
    cursor = 0
    while cursor < len(line):
        if comment_open:
            end = line.find("-->", cursor)
            if end < 0:
                for index in range(cursor, len(characters)):
                    characters[index] = " "
                return "".join(characters), True
            for index in range(cursor, min(end + 3, len(characters))):
                characters[index] = " "
            cursor = end + 3
            comment_open = False
        else:
            start = line.find("<!--", cursor)
            if start < 0:
                break
            end = line.find("-->", start + 4)
            if end < 0:
                for index in range(start, len(characters)):
                    characters[index] = " "
                return "".join(characters), True
            for index in range(start, min(end + 3, len(characters))):
                characters[index] = " "
            cursor = end + 3
    return "".join(characters), comment_open


def _mask_inline_code(line: str) -> str:
    characters = list(line)
    cursor = 0
    while cursor < len(line):
        if line[cursor] != "`":
            cursor += 1
            continue
        run_end = cursor
        while run_end < len(line) and line[run_end] == "`":
            run_end += 1
        delimiter = line[cursor:run_end]
        closing = line.find(delimiter, run_end)
        if closing < 0:
            cursor = run_end
            continue
        for index in range(cursor, closing + len(delimiter)):
            characters[index] = " "
        cursor = closing + len(delimiter)
    return "".join(characters)


def _iter_inline_code_values(text: str) -> Iterator[str]:
    """Yield inline-code contents while excluding fenced blocks and comments."""

    for line in _masked_markdown_lines(text, mask_inline_code=False):
        cursor = 0
        while cursor < len(line):
            if line[cursor] != "`":
                cursor += 1
                continue
            run_end = cursor
            while run_end < len(line) and line[run_end] == "`":
                run_end += 1
            delimiter = line[cursor:run_end]
            closing = line.find(delimiter, run_end)
            if closing < 0:
                break
            yield line[run_end:closing].strip()
            cursor = closing + len(delimiter)


def _masked_markdown_lines(
    text: str, *, mask_inline_code: bool = True
) -> list[str]:
    result: list[str] = []
    fence_character: str | None = None
    fence_length = 0
    comment_open = False
    for line in text.splitlines():
        fence_match = FENCE_RE.match(line)
        if fence_character is not None:
            if (
                fence_match
                and fence_match.group("fence")[0] == fence_character
                and len(fence_match.group("fence")) >= fence_length
            ):
                fence_character = None
                fence_length = 0
            result.append(" " * len(line))
            continue
        if fence_match:
            fence = fence_match.group("fence")
            fence_character = fence[0]
            fence_length = len(fence)
            result.append(" " * len(line))
            continue
        without_comments, comment_open = _mask_html_comments(line, comment_open)
        result.append(
            _mask_inline_code(without_comments)
            if mask_inline_code
            else without_comments
        )
    return result


def _iter_inline_destinations(line: str) -> Iterator[str]:
    cursor = 0
    while True:
        marker = line.find("](", cursor)
        if marker < 0:
            return
        position = marker + 2
        while position < len(line) and line[position].isspace():
            position += 1
        if position >= len(line):
            return
        if line[position] == "<":
            end = line.find(">", position + 1)
            if end >= 0:
                yield line[position : end + 1]
                cursor = end + 1
                continue
            cursor = position + 1
            continue

        destination: list[str] = []
        parenthesis_depth = 0
        while position < len(line):
            character = line[position]
            if character == "\\" and position + 1 < len(line):
                destination.extend((character, line[position + 1]))
                position += 2
                continue
            if character == "(":
                parenthesis_depth += 1
                destination.append(character)
                position += 1
                continue
            if character == ")":
                if parenthesis_depth == 0:
                    break
                parenthesis_depth -= 1
                destination.append(character)
                position += 1
                continue
            if character.isspace() and parenthesis_depth == 0:
                break
            destination.append(character)
            position += 1
        if destination:
            yield "".join(destination)
        cursor = max(position + 1, marker + 2)


def _iter_markdown_destinations(document: Document) -> Iterator[tuple[int, str]]:
    for line_number, line in enumerate(
        _masked_markdown_lines(document.text), start=1
    ):
        reference_match = REFERENCE_LINK_RE.match(line)
        if reference_match:
            yield line_number, reference_match.group("destination")
        for destination in _iter_inline_destinations(line):
            yield line_number, destination


def _reference_label_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _iter_active_markdown_destinations(
    document: Document,
) -> Iterator[tuple[int, str]]:
    """Yield destinations that are used by a link, not unused definitions."""

    lines = _masked_markdown_lines(document.text)
    definitions: dict[str, str] = {}
    for line in lines:
        match = REFERENCE_LINK_RE.match(line)
        if match:
            definitions[_reference_label_key(match.group("label"))] = match.group(
                "destination"
            )

    explicit_reference_re = re.compile(r"(?<!!)\[([^\]\r\n]+)\]\[([^\]\r\n]*)\]")
    shortcut_reference_re = re.compile(r"(?<![!\]])\[([^\]\r\n]+)\](?![\[(])")
    for line_number, line in enumerate(lines, start=1):
        if REFERENCE_LINK_RE.match(line):
            continue
        for destination in _iter_inline_destinations(line):
            yield line_number, destination
        occupied: list[tuple[int, int]] = []
        for match in explicit_reference_re.finditer(line):
            label = match.group(2) or match.group(1)
            destination = definitions.get(_reference_label_key(label))
            if destination is not None:
                occupied.append(match.span())
                yield line_number, destination
        for match in shortcut_reference_re.finditer(line):
            if any(start <= match.start() and match.end() <= end for start, end in occupied):
                continue
            destination = definitions.get(_reference_label_key(match.group(1)))
            if destination is not None:
                yield line_number, destination


def _markdown_unescape(value: str) -> str:
    return re.sub(r"\\([\\`*{}\[\]()#+.!_<>-])", r"\1", value)


def _destination_contains_placeholder(destination: str) -> bool:
    if BRACE_TOKEN_RE.search(destination):
        return True
    for match in ANGLE_TOKEN_RE.finditer(destination):
        body = match.group(1).strip()
        if not _is_placeholder_body(body):
            continue
        # Angle brackets are also valid Markdown syntax for real destinations
        # containing spaces.  A path separator or filename extension is a
        # stronger path clue than a placeholder clue here.
        if "/" in body or "\\" in body or re.search(r"\.[A-Za-z0-9]{1,12}$", body):
            continue
        return True
    return False


def _check_markdown_links(root: Path, documents: Sequence[Document]) -> list[Issue]:
    issues: list[Issue] = []
    for document in documents:
        for line_number, raw_destination in _iter_markdown_destinations(document):
            destination = html.unescape(raw_destination.strip())
            if _destination_contains_placeholder(destination):
                continue
            if destination.startswith("<") and destination.endswith(">"):
                destination = destination[1:-1].strip()
            if not destination or destination.startswith("#"):
                continue
            destination = _markdown_unescape(destination)

            if destination.startswith("//"):
                # Protocol-relative web URL.
                continue
            if (
                WINDOWS_ABSOLUTE_RE.match(destination)
                or destination.startswith(("\\\\", "/"))
                or destination.casefold().startswith("file:")
            ):
                issues.append(
                    Issue(
                        code="MARKDOWN_PATH_ESCAPE",
                        path=document.relative_path,
                        line=line_number,
                        message=f"Local Markdown target is absolute or outside the portable root: {destination!r}.",
                    )
                )
                continue
            if URI_SCHEME_RE.match(destination):
                continue

            path_part = re.split(r"[?#]", destination, maxsplit=1)[0]
            if not path_part:
                continue
            try:
                decoded_path = unquote_to_bytes(path_part).decode("utf-8", errors="strict")
            except UnicodeDecodeError:
                issues.append(
                    Issue(
                        code="MALFORMED_MARKDOWN_LINK",
                        path=document.relative_path,
                        line=line_number,
                        message=f"Markdown target is not valid percent-encoded UTF-8: {destination!r}.",
                    )
                )
                continue
            if "\x00" in decoded_path:
                issues.append(
                    Issue(
                        code="MALFORMED_MARKDOWN_LINK",
                        path=document.relative_path,
                        line=line_number,
                        message="Markdown target contains a NUL byte.",
                    )
                )
                continue

            native_path = decoded_path.replace("\\", os.sep).replace("/", os.sep)
            candidate = document.path.parent / native_path
            try:
                resolved_candidate = candidate.resolve(strict=False)
            except OSError as exc:
                raise WorkspaceReadError(
                    f"cannot resolve Markdown target {destination!r} in {document.path}: {exc}"
                ) from exc
            if not _is_within(resolved_candidate, root):
                issues.append(
                    Issue(
                        code="MARKDOWN_PATH_ESCAPE",
                        path=document.relative_path,
                        line=line_number,
                        message=f"Relative Markdown target escapes the audit root: {destination!r}.",
                    )
                )
                continue
            try:
                target_exists = candidate.exists()
            except OSError as exc:
                raise WorkspaceReadError(
                    f"cannot inspect Markdown target {destination!r} in {document.path}: {exc}"
                ) from exc
            if not target_exists:
                issues.append(
                    Issue(
                        code="BROKEN_MARKDOWN_LINK",
                        path=document.relative_path,
                        line=line_number,
                        message=f"Relative Markdown target does not exist: {destination!r}.",
                    )
                )
    return issues


def _clean_markdown_label(value: str) -> str:
    value = re.sub(r"[`*_~]", "", value)
    value = re.sub(r"\s+", " ", value.strip())
    return value.casefold()


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    return [cell.replace("\\|", "|").strip() for cell in re.split(r"(?<!\\)\|", stripped)]


def _is_separator_row(line: str) -> bool:
    cells = _split_table_row(line)
    return bool(cells) and all(TABLE_SEPARATOR_CELL_RE.fullmatch(cell.strip()) for cell in cells)


def _canonical_stable_id(value: str) -> str | None:
    cleaned = value.strip().strip("`*_~")
    link_match = re.fullmatch(r"\[([^\]]+)\]\([^)]*\)", cleaned)
    if link_match:
        cleaned = link_match.group(1).strip().strip("`*_~")
    if not cleaned or _destination_contains_placeholder(cleaned):
        return None
    if cleaned.casefold() in {"n/a", "na", "none", "null", "无", "不适用"}:
        return None
    if re.search(r"\s", cleaned) or len(cleaned) > 160:
        return None
    if not re.fullmatch(r"[^|,;，；:：]+(?::[^|,;，；:：]+)*", cleaned):
        return None
    return cleaned


def _document_defines_stable_ids(document: Document) -> bool:
    """Return true only for a document that confidently owns an ID registry.

    Status panels, startup entries, and long-term routing indexes routinely
    repeat IDs as pointers.  Treating every labelled occurrence as a
    definition makes those healthy routes look like competing authorities.
    Definition-oriented designs and registries are intentionally detected by
    role rather than by one mandatory filename.
    """

    if _is_status_document(document):
        return False
    if (
        "/" not in document.relative_path
        and document.path.name.casefold() in ENTRY_POINT_NAMES
    ):
        return False
    stem = document.path.stem.replace("-", " ").replace("_", " ")
    headings = " ".join(_heading_labels(document)[:3])
    return bool(DEFINITION_DOCUMENT_RE.search(f"{stem} {headings}"))


def _stable_id_label_role(label: str, document: Document) -> str | None:
    cleaned = _clean_markdown_label(label)
    is_reference = bool(REFERENCE_LABEL_RE.search(cleaned))
    is_definition = bool(DEFINITION_LABEL_RE.search(cleaned))

    base = re.sub(
        r"\b(?:authoritative|canonical|defined|definition|reference|referenced|"
        r"upstream|downstream|parent|source|dependency)\b",
        " ",
        cleaned,
        flags=re.I,
    )
    for token in (
        "权威",
        "规范",
        "定义",
        "引用",
        "参照",
        "上游",
        "下游",
        "父级",
        "来源",
        "依赖",
    ):
        base = base.replace(token, " ")
    base = re.sub(r"[-_()\[\]]+", " ", base)
    base = re.sub(r"\s+", " ", base).strip()
    if base not in EXPLICIT_ID_LABELS and not (
        base == "id" and (is_reference or is_definition)
    ):
        return None
    if is_reference:
        return "reference"
    if is_definition:
        return "definition"
    return "definition" if _document_defines_stable_ids(document) else "reference"


def _is_link_wrapped_id(value: str) -> bool:
    cleaned = value.strip().strip("`*_~")
    return bool(re.fullmatch(r"\[[^\]]+\]\([^)]*\)", cleaned))


def _explicit_stable_id_definitions(
    documents: Sequence[Document],
) -> list[tuple[str, str, int]]:
    definitions: list[tuple[str, str, int]] = []
    scalar_pattern = re.compile(
        r"^\s*(?:[-*+]\s+)?(?P<label>[^:：|]{1,100})\s*[:：]\s*"
        r"(?P<value>.+?)\s*$"
    )

    for document in documents:
        lines = _masked_markdown_lines(document.text)
        table_data_lines: set[int] = set()
        index = 0
        while index + 1 < len(lines):
            if "|" not in lines[index] or not _is_separator_row(lines[index + 1]):
                index += 1
                continue
            headers = _split_table_row(lines[index])
            definition_columns = [
                column
                for column, header in enumerate(headers)
                if _stable_id_label_role(header, document) == "definition"
            ]
            row_index = index + 2
            while (
                row_index < len(lines)
                and "|" in lines[row_index]
                and lines[row_index].strip()
            ):
                table_data_lines.add(row_index)
                cells = _split_table_row(lines[row_index])
                for column in definition_columns:
                    if column >= len(cells) or _is_link_wrapped_id(cells[column]):
                        continue
                    stable_id = _canonical_stable_id(cells[column])
                    if stable_id is not None:
                        definitions.append(
                            (stable_id, document.relative_path, row_index + 1)
                        )
                row_index += 1
            index = max(row_index, index + 1)

        for line_index, line in enumerate(lines):
            if line_index in table_data_lines:
                continue
            match = scalar_pattern.match(line)
            if not match:
                continue
            if _stable_id_label_role(match.group("label"), document) != "definition":
                continue
            if _is_link_wrapped_id(match.group("value")):
                continue
            stable_id = _canonical_stable_id(match.group("value"))
            if stable_id is not None:
                definitions.append(
                    (stable_id, document.relative_path, line_index + 1)
                )
    definitions.sort(
        key=lambda item: (
            item[1].casefold(),
            item[1],
            item[2],
            item[0].casefold(),
            item[0],
        )
    )
    return definitions


def _check_duplicate_stable_ids(documents: Sequence[Document]) -> list[Issue]:
    first_definition: dict[str, tuple[str, str, int]] = {}
    issues: list[Issue] = []
    for stable_id, path, line in _explicit_stable_id_definitions(documents):
        canonical_key = stable_id.casefold()
        if canonical_key not in first_definition:
            first_definition[canonical_key] = (stable_id, path, line)
            continue
        first_id, first_path, first_line = first_definition[canonical_key]
        issues.append(
            Issue(
                code="DUPLICATE_STABLE_ID",
                path=path,
                line=line,
                message=(
                    f"Stable ID {stable_id!r} duplicates its definition at "
                    f"{first_path}:{first_line} (first spelling: {first_id!r})."
                ),
            )
        )
    return issues


def _heading_labels(document: Document) -> list[str]:
    labels: list[str] = []
    for line in document.text.splitlines():
        match = re.match(r"^\ufeff?\s*#{1,6}\s+(.+?)\s*#*\s*$", line)
        if match:
            labels.append(_clean_markdown_label(match.group(1)))
    return labels


def _is_status_document(document: Document) -> bool:
    stem = document.path.stem.casefold().replace(" ", "_").replace("-", "_")
    if (
        stem in {"status", "current_status", "project_status", "workspace_status"}
        or stem.endswith("_status")
        or "状态" in stem
    ):
        return True
    headings = _heading_labels(document)
    if not headings:
        return False
    first_heading = headings[0]
    return bool(
        re.search(r"\b(?:current|project|workspace)\s+status\b", first_heading, re.I)
        or "当前状态" in first_heading
        or "状态面板" in first_heading
    )


def _status_field_names(label: str) -> set[str]:
    cleaned = _clean_markdown_label(label)
    return {
        field_name
        for field_name, patterns in STATUS_FIELD_PATTERNS.items()
        if any(pattern.search(cleaned) for pattern in patterns)
    }


def _strip_markdown_container_prefix(line: str) -> str:
    stripped = line.strip()
    stripped = re.sub(r"^(?:>\s*)+", "", stripped)
    stripped = re.sub(r"^(?:[-*+]\s+)", "", stripped)
    return stripped.strip()


def _status_value_fragment_is_meaningful(
    fragment: str, field_name: str
) -> bool:
    value = _strip_markdown_container_prefix(fragment)
    if not value or _is_separator_row(value):
        return False
    value = re.sub(r"^\[[ xX]\]\s*", "", value)
    value = value.strip().strip("`*_~").strip()
    if not value:
        return False

    lowered = re.sub(r"\s+", " ", value.casefold()).strip(" .,:;：；-—–")
    explicit_none = {
        "none",
        "no blocker",
        "no blockers",
        "n/a",
        "na",
        "无",
        "无阻塞",
        "无待决策",
        "不适用",
    }
    if field_name == "blockers/decisions" and lowered in explicit_none:
        return True

    if any(True for _ in _iter_placeholder_tokens(value)):
        return False
    if re.fullmatch(
        r"(?ix)(?:todo|tbd|unknown|placeholder|pending|not\s+set|"
        r"to\s+be\s+(?:filled|decided|determined)|n/?a|none|null|"
        r"待填写|待补充|待定|未定|未知|占位符|暂无)",
        lowered,
    ):
        return False
    return bool(re.search(r"[A-Za-z0-9\u3400-\u9fff]", value))


def _section_value_fragments(lines: Sequence[str]) -> list[str]:
    fragments: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if (
            "|" in line
            and index + 1 < len(lines)
            and _is_separator_row(lines[index + 1])
        ):
            # A table's column headings describe schema, not current state.
            index += 2
            continue
        if "|" in line:
            fragments.extend(_split_table_row(line))
        else:
            fragments.append(line)
        index += 1
    return fragments


def _status_field_values(document: Document) -> dict[str, list[str]]:
    values = {field_name: [] for field_name in STATUS_FIELD_PATTERNS}
    lines = _masked_markdown_lines(document.text, mask_inline_code=False)
    table_line_indices: set[int] = set()
    table_index = 0
    while table_index + 1 < len(lines):
        if "|" not in lines[table_index] or not _is_separator_row(
            lines[table_index + 1]
        ):
            table_index += 1
            continue
        headers = _split_table_row(lines[table_index])
        header_fields = [
            _status_field_names(header) for header in headers
        ]
        table_line_indices.update((table_index, table_index + 1))
        row_index = table_index + 2
        while (
            row_index < len(lines)
            and "|" in lines[row_index]
            and lines[row_index].strip()
        ):
            table_line_indices.add(row_index)
            cells = _split_table_row(lines[row_index])
            for column, field_names in enumerate(header_fields):
                if column >= len(cells):
                    continue
                for field_name in field_names:
                    values[field_name].append(cells[column])
            if len(cells) >= 2:
                for field_name in _status_field_names(cells[0]):
                    values[field_name].extend(cells[1:])
            row_index += 1
        table_index = max(row_index, table_index + 2)

    for index, raw_line in enumerate(lines):
        if index in table_line_indices:
            continue
        stripped = _strip_markdown_container_prefix(raw_line)
        if not stripped:
            continue

        heading = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", stripped)
        if heading:
            heading_text = heading.group(1).strip()
            label = heading_text
            inline_value = ""
            split = re.match(r"^([^:：]{1,100})\s*[:：]\s*(.*)$", heading_text)
            if split and _status_field_names(split.group(1)):
                label, inline_value = split.group(1), split.group(2)
            field_names = _status_field_names(label)
            if not field_names:
                continue
            end = index + 1
            while end < len(lines):
                candidate = _strip_markdown_container_prefix(lines[end])
                if re.match(r"^#{1,6}\s+", candidate):
                    break
                end += 1
            section_fragments = _section_value_fragments(lines[index + 1 : end])
            for field_name in field_names:
                if inline_value:
                    values[field_name].append(inline_value)
                values[field_name].extend(section_fragments)
            continue

        item = stripped.replace("**", "").replace("__", "")
        scalar = re.match(r"^([^:：|]{1,100})\s*[:：]\s*(.*)$", item)
        if not scalar:
            continue
        for field_name in _status_field_names(scalar.group(1)):
            values[field_name].append(scalar.group(2))
    return values


def _status_missing_fields(document: Document) -> list[str]:
    values = _status_field_values(document)
    return [
        field_name
        for field_name, candidates in values.items()
        if not any(
            _status_value_fragment_is_meaningful(candidate, field_name)
            for candidate in candidates
        )
    ]


def _first_frozen_trigger_line(document: Document) -> int | None:
    for line_number, line in enumerate(document.text.splitlines(), start=1):
        if FROZEN_TRIGGER_RE.search(line) and not FROZEN_NEGATION_RE.search(line):
            return line_number
    return None


def _check_status_files(documents: Sequence[Document]) -> tuple[list[str], list[Issue]]:
    status_documents = sorted(
        (document for document in documents if _is_status_document(document)),
        key=lambda document: _stable_text_key(document.relative_path),
    )
    issues: list[Issue] = []
    if not status_documents:
        issues.append(
            Issue(
                code="MISSING_STATUS_FILE",
                path=".",
                line=None,
                message=(
                    "No status document was found by filename or a current-status first heading."
                ),
            )
        )
        return [], issues

    for document in status_documents:
        missing_fields = _status_missing_fields(document)
        if missing_fields:
            issues.append(
                Issue(
                    code="STATUS_FIELDS_MISSING",
                    path=document.relative_path,
                    line=1,
                    message=(
                        "Missing or empty/placeholder minimum status fields: "
                        + ", ".join(missing_fields)
                        + "."
                    ),
                )
            )

        trigger_line = _first_frozen_trigger_line(document)
        if trigger_line is None:
            continue
        missing_clues: list[str] = []
        if not ARTIFACT_CLUE_RE.search(document.text):
            missing_clues.append("artifact path or explicit artifact/stable ID")
        if not IMMUTABLE_CLUE_RE.search(document.text):
            missing_clues.append("hash, commit/tag, or version/revision coordinate")
        if missing_clues:
            issues.append(
                Issue(
                    code="FROZEN_BASELINE_IDENTITY_MISSING",
                    path=document.relative_path,
                    line=trigger_line,
                    message=(
                        "Submitted/frozen baseline lacks identity clues: "
                        + "; ".join(missing_clues)
                        + "."
                    ),
                )
            )
    return [document.relative_path for document in status_documents], issues


def _resolve_existing_local_target(
    root: Path, document: Document, raw_destination: str
) -> Path | None:
    """Resolve a usable local link target without emitting duplicate issues."""

    destination = html.unescape(raw_destination.strip())
    if _destination_contains_placeholder(destination):
        return None
    if destination.startswith("<") and destination.endswith(">"):
        destination = destination[1:-1].strip()
    if not destination or destination.startswith("#"):
        return None
    destination = _markdown_unescape(destination)
    if (
        destination.startswith("//")
        or WINDOWS_ABSOLUTE_RE.match(destination)
        or destination.startswith(("\\\\", "/"))
        or destination.casefold().startswith("file:")
        or URI_SCHEME_RE.match(destination)
    ):
        return None
    path_part = re.split(r"[?#]", destination, maxsplit=1)[0]
    if not path_part:
        return None
    try:
        decoded_path = unquote_to_bytes(path_part).decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return None
    if "\x00" in decoded_path:
        return None
    native_path = decoded_path.replace("\\", os.sep).replace("/", os.sep)
    try:
        target = (document.path.parent / native_path).resolve(strict=False)
    except OSError as exc:
        raise WorkspaceReadError(
            f"cannot resolve Markdown target {destination!r} in {document.path}: {exc}"
        ) from exc
    if not _is_within(target, root):
        return None
    try:
        return target if target.exists() else None
    except OSError as exc:
        raise WorkspaceReadError(
            f"cannot inspect Markdown target {destination!r} in {document.path}: {exc}"
        ) from exc


def _build_local_link_graph(
    root: Path, documents: Sequence[Document]
) -> tuple[dict[str, set[str]], dict[str, bool]]:
    document_by_resolved: dict[Path, str] = {}
    for document in documents:
        try:
            document_by_resolved[document.path.resolve(strict=False)] = document.relative_path
        except OSError as exc:
            raise WorkspaceReadError(f"cannot resolve {document.path}: {exc}") from exc

    graph = {document.relative_path: set() for document in documents}
    target_is_file: dict[str, bool] = {
        document.relative_path: True for document in documents
    }
    for document in documents:
        destinations = [
            raw_destination
            for _, raw_destination in _iter_active_markdown_destinations(document)
        ]
        if _is_status_document(document):
            destinations.extend(
                value
                for value in _iter_inline_code_values(document.text)
                if (
                    "/" in value
                    or "\\" in value
                    or re.search(r"\.[A-Za-z0-9]{1,12}$", value)
                )
            )
        for raw_destination in destinations:
            target = _resolve_existing_local_target(root, document, raw_destination)
            if target is None:
                continue
            target_name = document_by_resolved.get(target)
            if target_name is None:
                target_name = _to_relative_posix(target, root)
            graph[document.relative_path].add(target_name)
            try:
                target_is_file[target_name] = target.is_file()
            except OSError as exc:
                raise WorkspaceReadError(f"cannot inspect {target}: {exc}") from exc
    return graph, target_is_file


def _status_parent_route_targets(
    root: Path,
    document: Document,
    document_by_resolved: dict[Path, str],
) -> set[str]:
    """Return targets explicitly labelled as the status panel's parent route."""

    targets: set[str] = set()
    for line in _masked_markdown_lines(document.text):
        item = _strip_markdown_container_prefix(line).replace("**", "").replace("__", "")
        scalar = re.match(r"^([^:：|]{1,100})\s*[:：]\s*(.*)$", item)
        if not scalar or "parent memory route" not in _status_field_names(
            scalar.group(1)
        ):
            continue
        for raw_destination in _iter_inline_destinations(scalar.group(2)):
            target = _resolve_existing_local_target(root, document, raw_destination)
            if target is None:
                continue
            targets.add(
                document_by_resolved.get(target, _to_relative_posix(target, root))
            )
    return targets


def _is_semantic_route_document(document: Document) -> bool:
    if _is_status_document(document):
        return False
    if (
        "/" not in document.relative_path
        and document.path.name.casefold() in ENTRY_POINT_NAMES
    ):
        return True
    stem = document.path.stem.replace("-", " ").replace("_", " ")
    headings = " ".join(_heading_labels(document)[:4])
    return bool(
        re.search(
            r"(?ix)(?:\b(?:long[\s-]*term\s+)?(?:workspace\s+)?memory\b|"
            r"\bworkspace\s+rules\b|\bstartup\s+route\b|\btask\s+routing\b|"
            r"\bproject\s+(?:map|navigation)\b|"
            r"工作记忆|长期记忆|协作规范|工作区规则|启动路由|任务路由|项目导航|恢复导航)",
            f"{stem} {headings}",
        )
    )


def _paths_to_status(
    graph: dict[str, set[str]],
    document_names: set[str],
    entry_points: Sequence[str],
    status_files: set[str],
) -> list[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set()
    for entry_point in entry_points:
        stack: list[tuple[str, tuple[str, ...]]] = [(entry_point, (entry_point,))]
        while stack:
            node, path = stack.pop()
            edge_count = len(path) - 1
            if node in status_files:
                paths.add(path)
                continue
            if edge_count >= 2:
                continue
            for target in sorted(graph.get(node, ()), key=_stable_text_key, reverse=True):
                if target not in document_names or target in path:
                    continue
                stack.append((target, path + (target,)))
    return sorted(paths, key=lambda path: tuple(_stable_text_key(item) for item in path))


def _check_three_hop_routes(
    root: Path,
    documents: Sequence[Document],
    entry_points: Sequence[str],
    status_files: Sequence[str],
) -> tuple[list[str], list[Issue]]:
    """Check a linked resumption path, allowing roles to share one document."""

    if not entry_points or not status_files:
        return [], []
    graph, target_is_file = _build_local_link_graph(root, documents)
    documents_by_name = {document.relative_path: document for document in documents}
    document_by_resolved: dict[Path, str] = {}
    for document in documents:
        try:
            document_by_resolved[document.path.resolve(strict=False)] = document.relative_path
        except OSError as exc:
            raise WorkspaceReadError(f"cannot resolve {document.path}: {exc}") from exc
    status_names = set(status_files)
    status_paths = _paths_to_status(
        graph, set(documents_by_name), entry_points, status_names
    )
    if not status_paths:
        return [], [
            Issue(
                code="THREE_HOP_ROUTE_MISSING",
                path=".",
                line=None,
                message=(
                    "No current-status document is reachable from a root startup "
                    "entry within two local Markdown-link hops."
                ),
            )
        ]

    route_nodes = {
        node
        for path in status_paths
        for node in path[:-1]
    }
    route_nodes.update(
        document.relative_path
        for document in documents
        if _is_semantic_route_document(document)
    )
    excluded_targets = route_nodes | status_names | set(entry_points)
    for status_name in status_names:
        excluded_targets.update(
            _status_parent_route_targets(
                root, documents_by_name[status_name], document_by_resolved
            )
        )
    routes: set[str] = set()
    for status_path in status_paths:
        status = status_path[-1]
        for target in graph.get(status, ()):
            if target in excluded_targets or not target_is_file.get(target, False):
                continue
            # status_path consumes at most two link edges; this final evidence
            # edge therefore keeps the complete startup route within three.
            routes.add(" -> ".join(status_path + (target,)))
    if routes:
        return sorted(routes, key=_stable_text_key), []
    return [], [
        Issue(
            code="THREE_HOP_ROUTE_MISSING",
            path=".",
            line=None,
            message=(
                "A startup-to-status route exists, but the reachable status does "
                "not link to local task evidence within the three-hop limit."
            ),
        )
    ]


def audit_workspace(root_argument: Path) -> AuditResult:
    try:
        root = root_argument.expanduser().resolve(strict=True)
    except OSError as exc:
        raise WorkspaceReadError(f"cannot resolve audit root {root_argument}: {exc}") from exc
    if not root.is_dir():
        raise WorkspaceReadError(f"audit root is not a directory: {root}")

    documents, issues = _collect_documents(root)
    entry_points = sorted(
        (
            document.relative_path
            for document in documents
            if document.path.parent == root
            and document.path.name.casefold() in ENTRY_POINT_NAMES
        ),
        key=_stable_text_key,
    )
    if not entry_points:
        issues.append(
            Issue(
                code="MISSING_ENTRY_POINT",
                path=".",
                line=None,
                message=(
                    "No root-level AGENTS.md, CLAUDE.md, README.md, or "
                    "WORKSPACE_RULES.md entry point was found."
                ),
            )
        )

    issues.extend(_check_markdown_links(root, documents))
    issues.extend(_check_placeholders(documents))
    issues.extend(_check_duplicate_stable_ids(documents))
    status_files, status_issues = _check_status_files(documents)
    issues.extend(status_issues)
    three_hop_routes, route_issues = _check_three_hop_routes(
        root, documents, entry_points, status_files
    )
    issues.extend(route_issues)
    issues.sort(key=_issue_key)

    return AuditResult(
        root=str(root),
        markdown_file_count=len(documents),
        entry_points=tuple(entry_points),
        status_files=tuple(status_files),
        three_hop_routes=tuple(three_hop_routes),
        issues=tuple(issues),
    )


def _render_text(result: AuditResult) -> str:
    lines = [
        f"Workspace memory audit: {result.root}",
        f"Markdown files read: {result.markdown_file_count}",
        "Entry points: " + (", ".join(result.entry_points) if result.entry_points else "none"),
        "Status files: " + (", ".join(result.status_files) if result.status_files else "none"),
        "Three-hop routes: "
        + ("; ".join(result.three_hop_routes) if result.three_hop_routes else "none"),
        f"Issues: {len(result.issues)}",
    ]
    if not result.issues:
        lines.append("OK: no issues found.")
        return "\n".join(lines)
    for issue in result.issues:
        location = issue.path
        if issue.line is not None:
            location += f":{issue.line}"
        lines.append(f"{location} [{issue.code}] {issue.message}")
    return "\n".join(lines)


def _render_json(result: AuditResult) -> str:
    payload = {
        "entry_points": list(result.entry_points),
        "issue_count": len(result.issues),
        "issues": [asdict(issue) for issue in result.issues],
        "markdown_file_count": result.markdown_file_count,
        "ok": not result.issues,
        "root": result.root,
        "status_files": list(result.status_files),
        "three_hop_routes": list(result.three_hop_routes),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def _render_error(message: str, output_format: str) -> str:
    if output_format == "json":
        return json.dumps(
            {"error": message, "ok": False},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    return "ERROR: " + message


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only audit of a file-based workspace memory system. "
            "Markdown is decoded as strict UTF-8; no content is repaired or changed."
        ),
        epilog=(
            "Checks: a root-level startup entry; relative Markdown targets and root "
            "escapes; unresolved template placeholders; duplicate explicit stable-ID "
            "definitions; minimum status fields (objective, verification time/method, "
            "parent route, current state, next action, blockers); and identity clues for "
            "submitted/frozen baselines; plus a linked entry-to-status-to-evidence route "
            "within three hops. Exit codes: 0=no issues, 1=issues found, "
            "2=usage, traversal, read, or UTF-8 decoding error."
        ),
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root to audit (default: current working directory).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _configure_utf8_streams()
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    try:
        result = audit_workspace(arguments.root)
    except WorkspaceReadError as exc:
        print(_render_error(str(exc), arguments.format), file=sys.stderr)
        return 2
    output = _render_json(result) if arguments.format == "json" else _render_text(result)
    print(output)
    return 0 if not result.issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
