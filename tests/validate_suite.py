#!/usr/bin/env python3
"""Dependency-free static release checks for Research Skills Suite.

This checker does not run unit tests, the official Skill validator, the Plugin
validator, or activation evaluations. Success is therefore reported as
STATIC PASS, never as a release pass.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.parse import unquote, urlsplit


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
EXPECTED_SKILL_SET = set(EXPECTED_SKILLS)
ALLOWED_FRONTMATTER_KEYS = {
    "name",
    "description",
    "license",
    "compatibility",
    "metadata",
    "allowed-tools",
}
TEXT_SUFFIXES = {
    "", ".bib", ".c", ".cfg", ".cff", ".cmd", ".conf", ".cpp", ".css",
    ".csv", ".dockerfile", ".gitattributes", ".gitignore", ".go", ".h",
    ".html", ".ini", ".java", ".js", ".json", ".jsx", ".kt", ".lock",
    ".md", ".properties", ".ps1", ".py", ".r", ".rb", ".rs", ".rst",
    ".sh", ".sql", ".svg", ".swift", ".template", ".tex", ".toml", ".ts",
    ".tsv", ".tsx", ".txt", ".xml", ".yaml", ".yml",
}
KNOWN_BINARY_SUFFIXES = {
    ".7z", ".bmp", ".doc", ".docx", ".eot", ".gif", ".gz", ".ico",
    ".jpeg", ".jpg", ".otf", ".parquet", ".pdf", ".png", ".ppt", ".pptx",
    ".tar", ".ttf", ".webp", ".woff", ".woff2", ".xls", ".xlsx", ".zip",
}
IGNORED_DIR_NAMES = {
    ".cache", ".git", ".hg", ".mypy_cache", ".nox", ".pytest_cache",
    ".ruff_cache", ".svn", ".tox", ".venv", "__pycache__", "build", "cache",
    "dist", "env", "node_modules", "venv",
}
IGNORED_DIR_PREFIXES = (".activation-", ".test-")
TEXT_FILE_NAMES = {
    ".editorconfig", ".gitattributes", ".gitignore", "Dockerfile", "LICENSE",
    "NOTICE", "VERSION",
}
PRIVACY_PATTERNS = {
    "absolute Windows path": re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/](?![\\/])"),
    "absolute user-home path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
    "file URI": re.compile(r"\bfile://", re.IGNORECASE),
    "64-character artifact hash": re.compile(
        r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{64}(?![A-Fa-f0-9])"
    ),
    "private-key block": re.compile(r"BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY"),
    "GitHub token": re.compile(
        r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"
    ),
    "OpenAI-style token": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    "bearer token": re.compile(
        r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE
    ),
    "JWT token": re.compile(
        r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
    ),
    "credential assignment": re.compile(
        r"\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|secret|password)"
        r"\s*[:=]\s*(?![\"'{\[]|\$\{)([A-Za-z0-9_./+=-]{16,})",
        re.IGNORECASE,
    ),
}
HASH_EXEMPT_FILES = {"SHA256SUMS"}
SENSITIVE_NAME_RE = re.compile(
    r"(?:^|/)(?:\.env(?:\.[^/]*)?|id_(?:rsa|dsa|ecdsa|ed25519)|"
    r"[^/]+\.(?:key|p12|pfx|pem))$",
    re.IGNORECASE,
)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
SEMVER_RE = re.compile(r"\d+\.\d+\.\d+")


@dataclass(frozen=True)
class Layout:
    repo_root: Path
    skills_root: Path
    kind: str


@dataclass
class Scan:
    files: list[Path]
    directories: list[Path]
    text: dict[Path, str]
    declared_binaries: set[Path]


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
        help="Flat suite source root or exported public Plugin root.",
    )
    parser.add_argument(
        "--deny-term",
        action="append",
        default=[],
        help="Project-specific term forbidden in content and path names.",
    )
    parser.add_argument(
        "--allow-binary",
        action="append",
        default=[],
        metavar="REPO_RELATIVE_PATH",
        help="Declare one intentionally reviewed binary file.",
    )
    return parser.parse_args()


def relative(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def should_ignore_dir(name: str) -> bool:
    return name in IGNORED_DIR_NAMES or name.startswith(IGNORED_DIR_PREFIXES)


def inventory_tree(root: Path, failures: list[str]) -> tuple[list[Path], list[Path]]:
    files: list[Path] = []
    directories: list[Path] = []

    def visit(directory: Path) -> None:
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name.casefold())
        except OSError as exc:
            failures.append(f"{relative(root, directory)}: cannot enumerate: {exc}")
            return
        for entry in entries:
            path = Path(entry.path)
            rel = relative(root, path)
            try:
                if entry.is_symlink():
                    failures.append(f"{rel}: symbolic links are not allowed")
                elif entry.is_dir(follow_symlinks=False):
                    if not should_ignore_dir(entry.name):
                        directories.append(path)
                        visit(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)
                else:
                    failures.append(f"{rel}: unsupported filesystem entry")
            except OSError as exc:
                failures.append(f"{rel}: cannot inspect: {exc}")

    visit(root)
    return sorted(files), sorted(directories)


def normalize_declared_path(root: Path, raw: str, failures: list[str]) -> Path | None:
    normalized = raw.strip().replace("\\", "/")
    pure = PurePosixPath(normalized)
    if not normalized or pure.is_absolute() or ".." in pure.parts:
        failures.append(
            f"invalid binary declaration {raw!r}; use a repository-relative path"
        )
        return None
    path = (root / Path(*pure.parts)).resolve()
    if not path.is_relative_to(root):
        failures.append(f"binary declaration escapes repository root: {raw!r}")
        return None
    return path


def load_binary_declarations(
    root: Path,
    files: list[Path],
    cli_values: Iterable[str],
    failures: list[str],
) -> set[Path]:
    declared: set[Path] = set()
    declaration_file = root / "BINARY_ALLOWLIST.txt"
    values = list(cli_values)
    if declaration_file in files:
        try:
            declaration_text = declaration_file.read_text(
                encoding="utf-8", errors="strict"
            )
        except (OSError, UnicodeError) as exc:
            failures.append(f"BINARY_ALLOWLIST.txt: invalid UTF-8: {exc}")
            declaration_text = ""
        values.extend(
            line.strip()
            for line in declaration_text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    for raw in values:
        path = normalize_declared_path(root, raw, failures)
        if path is not None:
            declared.add(path)
    file_set = {path.resolve() for path in files}
    for path in sorted(declared):
        if path not in file_set:
            failures.append(f"declared binary does not exist: {relative(root, path)}")
    return declared


def expects_utf8_text(path: Path) -> bool:
    return path.name in TEXT_FILE_NAMES or path.suffix.casefold() in TEXT_SUFFIXES


def load_scan(
    root: Path,
    files: list[Path],
    directories: list[Path],
    declared_binaries: set[Path],
    failures: list[str],
) -> Scan:
    text: dict[Path, str] = {}
    for path in files:
        try:
            data = path.read_bytes()
        except OSError as exc:
            failures.append(f"{relative(root, path)}: cannot read: {exc}")
            continue
        is_known_binary = path.suffix.casefold() in KNOWN_BINARY_SUFFIXES
        contains_nul = b"\x00" in data
        try:
            decoded = data.decode("utf-8", errors="strict")
            utf8_valid = True
        except UnicodeDecodeError:
            decoded = ""
            utf8_valid = False
        if path.resolve() in declared_binaries:
            if utf8_valid and not contains_nul and not is_known_binary:
                failures.append(
                    f"{relative(root, path)}: declared binary is ordinary UTF-8 text"
                )
            continue
        if is_known_binary or contains_nul:
            failures.append(
                f"{relative(root, path)}: binary file is not explicitly declared"
            )
        elif not utf8_valid:
            label = (
                "invalid UTF-8 text"
                if expects_utf8_text(path)
                else "unknown or undeclared binary"
            )
            failures.append(f"{relative(root, path)}: {label}")
        else:
            text[path] = decoded
    return Scan(files, directories, text, declared_binaries)


def detect_layout(root: Path, scan: Scan, failures: list[str]) -> Layout | None:
    flat = {
        path.parent.name
        for path in scan.files
        if path.name == "SKILL.md" and path.parent.parent == root
    }
    nested_root = root / "skills"
    nested = {
        path.parent.name
        for path in scan.files
        if path.name == "SKILL.md" and path.parent.parent == nested_root
    }
    if flat and nested:
        failures.append(
            "ambiguous layout: Skill directories exist both at root and root/skills"
        )
        return None
    if flat:
        layout = Layout(root, root, "flat-source")
        found = flat
    elif nested:
        layout = Layout(root, nested_root, "public-plugin")
        found = nested
    else:
        failures.append(
            "cannot locate Skill directories in flat-source or public-plugin layout"
        )
        return None
    if found != EXPECTED_SKILL_SET:
        failures.append(
            "layout must contain exactly 8 declared Skills; "
            f"missing={sorted(EXPECTED_SKILL_SET - found)}, "
            f"extra={sorted(found - EXPECTED_SKILL_SET)}"
        )
    expected_paths = {
        (layout.skills_root / name / "SKILL.md").resolve()
        for name in EXPECTED_SKILLS
    }
    all_skill_paths = {
        path.resolve() for path in scan.files if path.name == "SKILL.md"
    }
    for path in sorted(all_skill_paths - expected_paths):
        failures.append(
            f"{relative(root, path)}: SKILL.md is outside the declared Skill set"
        )
    return layout


def strip_yaml_comment(line: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
        elif char == "\\" and quote == '"':
            escaped = True
        elif quote is not None:
            if char == quote:
                quote = None
        elif char in {"'", '"'}:
            quote = char
        elif char == "#" and (index == 0 or line[index - 1].isspace()):
            return line[:index]
    return line


def unquote_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing frontmatter delimiter") from exc
    values: dict[str, str] = {}
    index = 1
    while index < end:
        raw = strip_yaml_comment(lines[index]).rstrip()
        index += 1
        if not raw.strip() or raw[:1].isspace():
            continue
        if ":" not in raw:
            raise ValueError(f"invalid top-level frontmatter line: {raw!r}")
        key, value = raw.split(":", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*", key):
            raise ValueError(f"invalid frontmatter key {key!r}")
        if key in values:
            raise ValueError(f"duplicate frontmatter key {key!r}")
        scalar = value.strip()
        if scalar in {"|", ">", "|-", ">-", "|+", ">+"}:
            block: list[str] = []
            while index < end:
                candidate = lines[index]
                if candidate and not candidate[:1].isspace():
                    break
                block.append(candidate.strip())
                index += 1
            scalar = "\n".join(block) if scalar.startswith("|") else " ".join(block)
        values[key] = unquote_scalar(scalar)
    return values


def parse_agent_sections(
    text: str,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    sections: dict[str, list[tuple[int, str, str]]] = {}
    current: str | None = None
    errors: list[str] = []
    seen_top: set[str] = set()
    for number, original in enumerate(text.splitlines(), start=1):
        line = strip_yaml_comment(original).rstrip()
        if not line.strip():
            continue
        leading = line[: len(line) - len(line.lstrip())]
        if "\t" in leading:
            errors.append(f"line {number}: tabs are not allowed for indentation")
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if indent == 0:
            if key in seen_top:
                errors.append(f"line {number}: duplicate top-level field {key!r}")
            seen_top.add(key)
            current = key if not value.strip() else None
            sections.setdefault(key, [])
        elif current is not None and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            sections[current].append((indent, key, value.strip()))
    direct: dict[str, dict[str, str]] = {}
    for section, entries in sections.items():
        if not entries:
            direct[section] = {}
            continue
        base_indent = min(indent for indent, _key, _value in entries)
        values: dict[str, str] = {}
        for _indent, key, value in (
            entry for entry in entries if entry[0] == base_indent
        ):
            if key in values:
                errors.append(f"section {section!r}: duplicate field {key!r}")
            values[key] = value
        direct[section] = values
    return direct, errors


def get_text(
    scan: Scan, path: Path, root: Path, failures: list[str]
) -> str | None:
    if path not in scan.files:
        failures.append(f"missing required file: {relative(root, path)}")
        return None
    return scan.text.get(path)


def check_version(
    layout: Layout, scan: Scan, failures: list[str]
) -> str | None:
    root = layout.repo_root
    version_text = get_text(scan, root / "VERSION", root, failures)
    readme = get_text(scan, root / "README.md", root, failures)
    changelog = get_text(scan, root / "CHANGELOG.md", root, failures)
    if version_text is None or readme is None or changelog is None:
        return None
    version = version_text.strip()
    if SEMVER_RE.fullmatch(version) is None:
        failures.append(f"VERSION is not strict semantic version: {version!r}")
    version_marker = "Suite version: " + chr(96) + version + chr(96)
    if version_marker not in readme:
        failures.append("README suite version does not match VERSION")
    if not re.search(rf"^## {re.escape(version)}\s+-", changelog, re.MULTILINE):
        failures.append("CHANGELOG has no heading for VERSION")
    return version


def check_skills(
    layout: Layout, scan: Scan, failures: list[str]
) -> set[str]:
    root = layout.repo_root
    names: set[str] = set()
    for directory_name in EXPECTED_SKILLS:
        skill_dir = layout.skills_root / directory_name
        skill_path = skill_dir / "SKILL.md"
        text = get_text(scan, skill_path, root, failures)
        if text is None:
            continue
        try:
            frontmatter = parse_frontmatter(text)
        except ValueError as exc:
            failures.append(f"{relative(root, skill_path)}: {exc}")
            continue
        unsupported = sorted(set(frontmatter) - ALLOWED_FRONTMATTER_KEYS)
        if unsupported:
            failures.append(
                f"{relative(root, skill_path)}: unsupported frontmatter keys "
                f"{unsupported}"
            )
        name = frontmatter.get("name", "").strip()
        description = frontmatter.get("description", "").strip()
        if not name:
            failures.append(
                f"{relative(root, skill_path)}: missing required frontmatter name"
            )
        elif name != directory_name:
            failures.append(
                f"{relative(root, skill_path)}: name does not match directory"
            )
        if not re.fullmatch(r"[a-z0-9-]{1,64}", name):
            failures.append(
                f"{relative(root, skill_path)}: invalid skill name {name!r}"
            )
        if not description:
            failures.append(
                f"{relative(root, skill_path)}: missing required description"
            )
        elif len(description) > 1024:
            failures.append(
                f"{relative(root, skill_path)}: description exceeds 1024 characters"
            )
        if name:
            names.add(name)

        agent_path = skill_dir / "agents" / "openai.yaml"
        agent_text = get_text(scan, agent_path, root, failures)
        if agent_text is not None:
            sections, yaml_errors = parse_agent_sections(agent_text)
            for error in yaml_errors:
                failures.append(f"{relative(root, agent_path)}: {error}")
            interface = sections.get("interface", {})
            policy = sections.get("policy", {})
            for field in ("display_name", "short_description", "default_prompt"):
                if not unquote_scalar(interface.get(field, "")):
                    failures.append(
                        f"{relative(root, agent_path)}: missing interface.{field}"
                    )
            default_prompt = unquote_scalar(interface.get("default_prompt", ""))
            expected_invocation = "$" + directory_name
            if default_prompt and expected_invocation not in default_prompt:
                failures.append(
                    f"{relative(root, agent_path)}: default prompt does not name "
                    f"{expected_invocation}"
                )
            implicit = policy.get("allow_implicit_invocation", "").strip()
            if implicit != "true":
                failures.append(
                    f"{relative(root, agent_path)}: "
                    "policy.allow_implicit_invocation must be an actual boolean true"
                )

        references = skill_dir / "references"
        for nested in scan.files:
            if nested.is_relative_to(references) and nested.parent != references:
                failures.append(
                    f"{relative(root, nested)}: references must remain one level deep"
                )
    if names != EXPECTED_SKILL_SET:
        failures.append(
            "parsed Skill names do not equal the declared 8-Skill set: "
            f"{sorted(names)}"
        )
    return names


def markdown_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    return target.split(maxsplit=1)[0] if target else ""


def check_links(layout: Layout, scan: Scan, failures: list[str]) -> None:
    root = layout.repo_root
    markdown_files = (
        path for path in scan.files if path.suffix.casefold() == ".md"
    )
    for path in sorted(markdown_files):
        text = scan.text.get(path)
        if text is None:
            continue
        for raw_target in LINK_RE.findall(text):
            target = markdown_target(raw_target)
            lowered = target.casefold()
            if (
                not target
                or target.startswith("#")
                or lowered.startswith(("http://", "https://", "mailto:"))
            ):
                continue
            target = unquote(target.split("#", 1)[0].split("?", 1)[0])
            resolved = (path.parent / target).resolve()
            if not resolved.is_relative_to(root):
                failures.append(
                    f"{relative(root, path)}: local link escapes repository root: "
                    f"{raw_target!r}"
                )
            elif not resolved.exists():
                failures.append(
                    f"{relative(root, path)}: broken link {raw_target!r}"
                )


def parse_skill_set(value: str) -> set[str]:
    value = (value or "").strip()
    if value == "none":
        return set()
    return {name.strip() for name in value.split("+") if name.strip()}


def check_golden_prompts(
    layout: Layout, scan: Scan, failures: list[str]
) -> None:
    root = layout.repo_root
    path = root / "tests" / "golden-prompts.tsv"
    content = get_text(scan, path, root, failures)
    if content is None:
        return
    reader = csv.DictReader(io.StringIO(content, newline=""), delimiter="\t")
    expected_columns = [
        "id",
        "target_skill",
        "expected_skills",
        "forbidden_skills",
        "class",
        "prompt",
        "expected_behavior",
    ]
    if reader.fieldnames != expected_columns:
        failures.append(f"{relative(root, path)}: expected columns {expected_columns}")
        return
    seen: set[str] = set()
    seen_prompts: set[str] = set()
    allowed_classes = {
        "direct", "indirect", "incomplete", "boundary", "composition", "negative",
    }
    coverage: dict[str, set[str]] = {name: set() for name in EXPECTED_SKILLS}
    for row_number, row in enumerate(reader, start=2):
        row_id = (row["id"] or "").strip()
        if not row_id or row_id in seen:
            failures.append(
                f"{relative(root, path)}:{row_number}: empty or duplicate id"
            )
        seen.add(row_id)
        prompt = (row["prompt"] or "").strip()
        if not prompt:
            failures.append(f"{relative(root, path)}:{row_number}: empty prompt")
        elif prompt in seen_prompts:
            failures.append(f"{relative(root, path)}:{row_number}: duplicate prompt")
        seen_prompts.add(prompt)
        if not (row["expected_behavior"] or "").strip():
            failures.append(
                f"{relative(root, path)}:{row_number}: empty expected_behavior"
            )
        target = (row["target_skill"] or "").strip()
        if target not in EXPECTED_SKILL_SET:
            failures.append(
                f"{relative(root, path)}:{row_number}: "
                f"unknown target_skill {target!r}"
            )
            continue
        case_class = (row["class"] or "").strip()
        if case_class not in allowed_classes:
            failures.append(
                f"{relative(root, path)}:{row_number}: invalid class {case_class!r}"
            )
            continue
        coverage[target].add(case_class)
        expected_skills = parse_skill_set(row["expected_skills"])
        forbidden_skills = parse_skill_set(row["forbidden_skills"])
        for field, values in (
            ("expected", expected_skills),
            ("forbidden", forbidden_skills),
        ):
            for name in sorted(values - EXPECTED_SKILL_SET):
                failures.append(
                    f"{relative(root, path)}:{row_number}: "
                    f"unknown {field} skill {name!r}"
                )
        overlap = expected_skills & forbidden_skills
        if overlap:
            failures.append(
                f"{relative(root, path)}:{row_number}: "
                f"skills both expected and forbidden: {sorted(overlap)}"
            )
        if (
            case_class in {"direct", "indirect", "incomplete"}
            and target not in expected_skills
        ):
            failures.append(
                f"{relative(root, path)}:{row_number}: "
                f"{case_class} case must expect target_skill"
            )
        if (
            case_class in {"negative", "boundary"}
            and target not in forbidden_skills
        ):
            failures.append(
                f"{relative(root, path)}:{row_number}: "
                f"{case_class} case must forbid target_skill"
            )
        if case_class == "composition" and (
            target not in expected_skills or len(expected_skills) < 2
        ):
            failures.append(
                f"{relative(root, path)}:{row_number}: "
                "composition must expect target and another skill"
            )
    for name in EXPECTED_SKILLS:
        missing = sorted(allowed_classes - coverage[name])
        if missing:
            failures.append(
                f"{relative(root, path)}: {name} lacks golden classes {missing}"
            )


def check_automation(
    layout: Layout, scan: Scan, failures: list[str]
) -> None:
    root = layout.repo_root
    required_tools = (
        root / "tests" / "validate_suite.py",
        root / "tests" / "score_activation_results.py",
        root / "tests" / "run_release_checks.py",
        root / "scripts" / "export_release_candidate.py",
    )
    for path in required_tools:
        if path not in scan.files:
            failures.append(
                f"missing release automation: {relative(root, path)}"
            )
    allowed_roots = [root / "tests", root / "scripts"]
    allowed_roots.extend(
        layout.skills_root / name / "scripts" for name in EXPECTED_SKILLS
    )
    for path in sorted(
        path for path in scan.files if path.suffix.casefold() == ".py"
    ):
        if not any(
            path == allowed or path.is_relative_to(allowed)
            for allowed in allowed_roots
        ):
            failures.append(
                f"{relative(root, path)}: "
                "Python automation is in an undeclared location"
            )
        source = scan.text.get(path)
        if source is None:
            continue
        try:
            compile(source, str(path), "exec")
        except SyntaxError as exc:
            failures.append(
                f"{relative(root, path)}:{exc.lineno}: "
                f"script does not compile: {exc.msg}"
            )
    for path in sorted(
        path
        for path in scan.files
        if path.name.casefold().endswith(".json.template")
        and any(
            path.is_relative_to(layout.skills_root / name / "assets")
            for name in EXPECTED_SKILLS
        )
    ):
        content = scan.text.get(path)
        if content is None:
            continue
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            failures.append(
                f"{relative(root, path)}:{exc.lineno}: "
                f"invalid JSON template: {exc.msg}"
            )


def check_paths_and_privacy(
    layout: Layout,
    scan: Scan,
    deny_terms: list[str],
    failures: list[str],
) -> None:
    root = layout.repo_root
    terms = [(term, term.casefold()) for term in deny_terms if term]
    for path in sorted([*scan.directories, *scan.files]):
        rel = relative(root, path)
        if SENSITIVE_NAME_RE.search(rel):
            failures.append(f"{rel}: sensitive filename or directory name")
        folded = rel.casefold()
        for original, normalized in terms:
            if normalized in folded:
                failures.append(f"{rel}: path contains denied term {original!r}")
    for path, text in sorted(scan.text.items()):
        rel = relative(root, path)
        for label, pattern in PRIVACY_PATTERNS.items():
            if (
                label == "64-character artifact hash"
                and rel in HASH_EXEMPT_FILES
            ):
                continue
            match = pattern.search(text)
            if match:
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                if line_end < 0:
                    line_end = len(text)
                source_line = text[line_start:line_end]
                synthetic_target = (
                    'Target="' + "file:" + "///" + "C:" + "/private/source.txt" + '"'
                )
                safe_docx_fixture = (
                    rel == "tests/test_audit_docx_package.py"
                    and label in {"absolute Windows path", "file URI"}
                    and synthetic_target in source_line
                )
                if safe_docx_fixture:
                    continue
                line = text.count("\n", 0, match.start()) + 1
                failures.append(f"{rel}:{line}: possible {label}")
        folded = text.casefold()
        for original, normalized in terms:
            if normalized in folded:
                failures.append(f"{rel}: contains denied term {original!r}")


def is_real_https_url(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    parsed = urlsplit(value)
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and not parsed.username
    )


def contains_placeholder(value: object) -> bool:
    marker = re.compile(
        r"(?:\bTODO\b|\bTBD\b|placeholder|example\.com|"
        r"your[-_ ](?:name|org|url)|local developer|change[-_ ]?me)",
        re.IGNORECASE,
    )
    if isinstance(value, str):
        return marker.search(value) is not None
    if isinstance(value, list):
        return any(contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(contains_placeholder(item) for item in value.values())
    return False


def check_public_metadata(
    layout: Layout,
    scan: Scan,
    version: str | None,
    failures: list[str],
) -> None:
    if layout.kind != "public-plugin":
        return
    root = layout.repo_root
    plugin_path = root / ".codex-plugin" / "plugin.json"
    release_path = root / "RELEASE_MANIFEST.json"
    sums_path = root / "SHA256SUMS"
    plugin_text = get_text(scan, plugin_path, root, failures)
    release_text = get_text(scan, release_path, root, failures)
    sums_text = get_text(scan, sums_path, root, failures)
    if plugin_text is None or release_text is None or sums_text is None:
        return
    try:
        plugin = json.loads(plugin_text)
        release = json.loads(release_text)
    except json.JSONDecodeError as exc:
        failures.append(
            f"public manifest JSON is invalid: line {exc.lineno}: {exc.msg}"
        )
        return
    if not isinstance(plugin, dict) or not isinstance(release, dict):
        failures.append("public manifests must contain JSON objects")
        return
    if plugin.get("name") != root.name:
        failures.append(
            "plugin.json name must match the public Plugin root directory"
        )
    if not isinstance(plugin.get("name"), str) or not re.fullmatch(
        r"[a-z0-9-]{1,64}", plugin.get("name", "")
    ):
        failures.append("plugin.json name must be lower-case hyphen-case")
    if plugin.get("skills") != "./skills/":
        failures.append("plugin.json skills path must be './skills/'")
    if version is not None and plugin.get("version") != version:
        failures.append("plugin.json version does not match VERSION")
    if not str(plugin.get("description", "")).strip():
        failures.append("plugin.json description is required")
    author = plugin.get("author")
    interface = plugin.get("interface")
    if not isinstance(author, dict) or not str(author.get("name", "")).strip():
        failures.append("plugin.json author.name is required")
    elif not is_real_https_url(author.get("url")):
        failures.append("plugin.json author.url must be a real https URL")
    if not isinstance(interface, dict):
        failures.append("plugin.json interface object is required")
    else:
        for field in (
            "displayName",
            "shortDescription",
            "longDescription",
            "developerName",
            "category",
            "defaultPrompt",
        ):
            if field not in interface or not interface[field]:
                failures.append(f"plugin.json interface.{field} is required")
    for field in ("homepage", "repository"):
        if not is_real_https_url(plugin.get(field)):
            failures.append(f"plugin.json {field} must be a real https URL")
    if contains_placeholder(plugin) or contains_placeholder(release):
        failures.append("public manifests contain placeholder metadata")
    if release.get("plugin_name") != plugin.get("name"):
        failures.append("RELEASE_MANIFEST plugin_name does not match plugin.json")
    if version is not None and release.get("version") != version:
        failures.append("RELEASE_MANIFEST version does not match VERSION")
    if release.get("skills") != list(EXPECTED_SKILLS):
        failures.append(
            "RELEASE_MANIFEST skills must be the sorted declared 8-Skill set"
        )
    if release.get("license") != plugin.get("license"):
        failures.append("RELEASE_MANIFEST license does not match plugin.json")
    publisher = release.get("publisher")
    if (
        not isinstance(publisher, dict)
        or not str(publisher.get("name", "")).strip()
        or not is_real_https_url(publisher.get("url"))
    ):
        failures.append("RELEASE_MANIFEST publisher metadata is incomplete")
    for field in ("repository_url", "homepage_url", "support_url"):
        if not is_real_https_url(release.get(field)):
            failures.append(f"RELEASE_MANIFEST {field} must be a real https URL")
    if release.get("source_layout") != "flat-suite-source":
        failures.append("RELEASE_MANIFEST source_layout is invalid")
    if release.get("export_layout") != "public-root-with-skills":
        failures.append("RELEASE_MANIFEST export_layout is invalid")
    inventory = release.get("inventory")
    if not isinstance(inventory, dict) or inventory.get("path") != "SHA256SUMS":
        failures.append("RELEASE_MANIFEST inventory path must be SHA256SUMS")
        inventory = {}
    if inventory.get("algorithm") != "SHA-256":
        failures.append("RELEASE_MANIFEST inventory algorithm must be SHA-256")
    if inventory.get("scope") != "all regular files except SHA256SUMS":
        failures.append("RELEASE_MANIFEST inventory scope is invalid")
    if root / "PLUGIN_RELEASE.md" in scan.files:
        failures.append("internal PLUGIN_RELEASE.md must not enter a public candidate")
    declared: dict[str, str] = {}
    for number, line in enumerate(sums_text.splitlines(), start=1):
        match = re.fullmatch(r"([0-9a-f]{64})  ([^\r\n]+)", line)
        if match is None:
            failures.append(f"SHA256SUMS:{number}: invalid checksum line")
            continue
        digest, rel = match.groups()
        if rel in declared:
            failures.append(f"SHA256SUMS:{number}: duplicate path {rel!r}")
        declared[rel] = digest
    expected_files = {
        relative(root, path): path for path in scan.files if path != sums_path
    }
    missing = sorted(set(expected_files) - set(declared))
    extra = sorted(set(declared) - set(expected_files))
    if missing or extra:
        failures.append(
            "SHA256SUMS is not an exact inventory; "
            f"missing={missing}, extra={extra}"
        )
    for rel in sorted(set(expected_files) & set(declared)):
        actual = hashlib.sha256(expected_files[rel].read_bytes()).hexdigest()
        if actual != declared[rel]:
            failures.append(f"SHA256SUMS digest mismatch: {rel}")
    file_count = inventory.get("file_count")
    if file_count != len(expected_files):
        failures.append(
            "RELEASE_MANIFEST inventory.file_count is "
            f"{file_count!r}; expected {len(expected_files)}"
        )


def main() -> int:
    configure_utf8_streams()
    args = parse_args()
    root = args.root.expanduser().resolve()
    failures: list[str] = []
    if not root.is_dir():
        print(f"FAIL: root is not a directory: {root}")
        print("RESULT: STATIC FAIL (1 issue(s))")
        return 1
    if args.root.is_symlink():
        failures.append("repository root itself must not be a symbolic link")
    files, directories = inventory_tree(root, failures)
    declared = load_binary_declarations(root, files, args.allow_binary, failures)
    scan = load_scan(root, files, directories, declared, failures)
    layout = detect_layout(root, scan, failures)
    if layout is not None:
        for item in ("VERSION", "README.md", "CHANGELOG.md", "LICENSE", "NOTICE"):
            if root / item not in scan.files:
                failures.append(f"missing required file: {item}")
        version = check_version(layout, scan, failures)
        check_skills(layout, scan, failures)
        check_links(layout, scan, failures)
        check_golden_prompts(layout, scan, failures)
        check_automation(layout, scan, failures)
        check_paths_and_privacy(layout, scan, args.deny_term, failures)
        check_public_metadata(layout, scan, version, failures)
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(f"RESULT: STATIC FAIL ({len(failures)} issue(s))")
        return 1
    assert layout is not None
    print(f"RESULT: STATIC PASS (layout={layout.kind}; skills=8)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
