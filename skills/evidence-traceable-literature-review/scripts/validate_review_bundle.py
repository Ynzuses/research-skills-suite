#!/usr/bin/env python3
"""Validate the structural integrity of an evidence-review bundle.

The validator is deliberately limited to deterministic package checks.  It
does not decide whether a source scientifically supports a claim.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Iterable, Sequence


SEARCH_FILE = "search-ledger.tsv"
SCREENING_FILE = "screening-ledger.tsv"
EVIDENCE_FILE = "evidence-matrix.tsv"
SOURCE_FILE = "source-manifest.tsv"

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    SEARCH_FILE: (
        "search_id",
        "source",
        "executed_date",
        "query",
        "filters",
        "boundary",
        "raw_count",
        "saved_count",
        "output_path",
        "status",
        "notes",
    ),
    SCREENING_FILE: (
        "record_id",
        "search_id",
        "source_id",
        "title",
        "year",
        "stage",
        "decision",
        "decision_round",
        "current",
        "supersedes",
        "reason",
        "evidence_role",
        "notes",
    ),
    EVIDENCE_FILE: (
        "evidence_id",
        "claim_id",
        "claim_text",
        "claim_status",
        "source_id",
        "source_role",
        "locator",
        "evidence_excerpt",
        "scope",
        "direction",
        "strength",
        "intended_use",
        "notes",
    ),
    SOURCE_FILE: (
        "source_id",
        "citation",
        "stable_id",
        "version",
        "evidence_role",
        "full_text_status",
        "full_text_path",
        "sha256",
        "notes",
    ),
}

SEARCH_STATUSES = frozenset({"complete", "partial", "failed"})
SCREENING_STAGES = frozenset({"retrieved", "title", "abstract", "full_text"})
SCREENING_DECISIONS = frozenset({"include", "exclude", "pending"})
CLAIM_STATUSES = frozenset(
    {"fact", "synthesis", "hypothesis", "method_decision", "unresolved"}
)
SOURCE_ROLES = frozenset(
    {"original_study", "validation", "review", "database", "software", "background", "other"}
)
FULL_TEXT_STATUSES = frozenset({"present", "unavailable", "not_required"})
DIRECTIONS = frozenset({"supports", "contradicts", "limits", "does_not_address"})
STRENGTHS = frozenset({"direct", "indirect", "triangulating", "insufficient"})
INTENDED_USES = frozenset(
    {"background", "method", "result", "limitation", "interpretation", "other"}
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
NONNEGATIVE_INTEGER_RE = re.compile(r"^(0|[1-9][0-9]*)$")
POSITIVE_INTEGER_RE = re.compile(r"^[1-9][0-9]*$")
ISO_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
BOOLEAN_VALUES = frozenset({"true", "false"})


@dataclass(frozen=True)
class Issue:
    severity: str
    code: str
    file: str
    row: int | None
    message: str


@dataclass(frozen=True)
class TableRow:
    file: str
    line: int
    values: dict[str, str]


@dataclass(frozen=True)
class ScreeningDecision:
    row: TableRow
    record_id: str | None
    source_id: str
    decision: str | None
    decision_round: int | None
    current: bool | None
    supersedes: tuple[str, ...]


class BundleValidator:
    def __init__(self, bundle: Path, *, strict_release: bool = False) -> None:
        self.bundle = bundle.resolve()
        self.strict_release = strict_release
        self.issues: list[Issue] = []
        self.read_failed = False

    def add(
        self,
        severity: str,
        code: str,
        file: str,
        row: int | None,
        message: str,
    ) -> None:
        self.issues.append(Issue(severity, code, file, row, message))

    def error(self, code: str, row: TableRow | None, message: str, *, file: str = "") -> None:
        self.add(
            "error",
            code,
            row.file if row is not None else file,
            row.line if row is not None else None,
            message,
        )

    def warning(self, code: str, row: TableRow | None, message: str, *, file: str = "") -> None:
        self.add(
            "error" if self.strict_release else "warning",
            code,
            row.file if row is not None else file,
            row.line if row is not None else None,
            message,
        )

    def read_error(self, code: str, file: str, message: str) -> None:
        self.read_failed = True
        self.add("error", code, file, None, message)

    def load_table(self, filename: str) -> list[TableRow]:
        path = self.bundle / filename
        try:
            exists = path.exists()
            is_file = path.is_file()
        except OSError as exc:
            self.read_error("read_error", filename, f"could not inspect TSV path: {exc}")
            return []
        if not exists:
            self.read_error("missing_file", filename, "required TSV file is missing")
            return []
        if not is_file:
            self.read_error("not_a_file", filename, "required TSV path is not a regular file")
            return []

        try:
            with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
                raw_rows = list(csv.reader(handle, delimiter="\t", strict=True))
        except UnicodeDecodeError as exc:
            self.read_error(
                "invalid_utf8",
                filename,
                f"file is not strict UTF-8: byte {exc.start}",
            )
            return []
        except (OSError, csv.Error) as exc:
            self.read_error("read_error", filename, f"could not read TSV: {exc}")
            return []

        if not raw_rows:
            self.error("missing_header", None, "TSV is empty", file=filename)
            return []

        expected = list(TABLE_COLUMNS[filename])
        header = raw_rows[0]
        if header != expected:
            self.error(
                "header_mismatch",
                None,
                f"expected columns {expected!r}; found {header!r}",
                file=filename,
            )
            return []

        rows: list[TableRow] = []
        for line, cells in enumerate(raw_rows[1:], start=2):
            if not cells or all(cell == "" for cell in cells):
                continue
            if len(cells) != len(expected):
                self.add(
                    "error",
                    "row_width",
                    filename,
                    line,
                    f"expected {len(expected)} fields; found {len(cells)}",
                )
                continue
            if any("\x00" in cell for cell in cells):
                self.add("error", "nul_character", filename, line, "NUL characters are not allowed")
                continue
            rows.append(TableRow(filename, line, dict(zip(expected, cells))))
        return rows

    def require(self, row: TableRow, field: str) -> str | None:
        value = row.values[field].strip()
        if not value:
            self.error("missing_required_value", row, f"{field} is required")
            return None
        return value

    def enum(self, row: TableRow, field: str, allowed: frozenset[str]) -> str | None:
        value = self.require(row, field)
        if value is not None and value not in allowed:
            self.error(
                "invalid_enum",
                row,
                f"{field} must be one of {sorted(allowed)!r}; found {value!r}",
            )
            return None
        return value

    def unique_ids(self, rows: Iterable[TableRow], field: str) -> dict[str, TableRow]:
        registry: dict[str, TableRow] = {}
        for row in rows:
            value = self.require(row, field)
            if value is None:
                continue
            if value in registry:
                first = registry[value]
                self.error(
                    "duplicate_id",
                    row,
                    f"{field} {value!r} duplicates {first.file}:{first.line}",
                )
            else:
                registry[value] = row
        return registry

    def validate_relative_file_path(self, row: TableRow, raw_path: str) -> Path | None:
        value = raw_path.strip()
        if not value:
            self.error("missing_full_text_path", row, "full_text_path is required when status is present")
            return None
        if "\x00" in value:
            self.error("invalid_full_text_path", row, "full_text_path contains a NUL character")
            return None

        windows_path = PureWindowsPath(value)
        portable_value = value.replace("\\", "/")
        posix_path = PurePosixPath(portable_value)
        if windows_path.is_absolute() or windows_path.drive or posix_path.is_absolute():
            self.error("absolute_full_text_path", row, "full_text_path must be relative to the bundle")
            return None
        if any(part == ".." for part in posix_path.parts):
            self.error("full_text_path_escape", row, "full_text_path must not contain '..'")
            return None
        if not posix_path.parts or all(part in {"", "."} for part in posix_path.parts):
            self.error("invalid_full_text_path", row, "full_text_path must identify a file")
            return None

        candidate = self.bundle.joinpath(*posix_path.parts)
        try:
            resolved = candidate.resolve(strict=False)
            common = os.path.commonpath((str(self.bundle), str(resolved)))
        except (OSError, ValueError) as exc:
            self.error("invalid_full_text_path", row, f"could not resolve full_text_path: {exc}")
            return None
        if os.path.normcase(common) != os.path.normcase(str(self.bundle)):
            self.error("full_text_path_escape", row, "full_text_path resolves outside the bundle")
            return None
        if not resolved.exists():
            self.error("missing_full_text", row, f"full text does not exist: {portable_value}")
            return None
        if not resolved.is_file():
            self.error("full_text_not_file", row, f"full text is not a regular file: {portable_value}")
            return None
        return resolved

    def file_sha256(self, path: Path, row: TableRow) -> str | None:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError as exc:
            self.read_failed = True
            self.error("full_text_read_error", row, f"could not hash full text: {exc}")
            return None
        return digest.hexdigest()

    def validate(self) -> list[Issue]:
        tables = {name: self.load_table(name) for name in TABLE_COLUMNS}
        searches = tables[SEARCH_FILE]
        screenings = tables[SCREENING_FILE]
        evidence = tables[EVIDENCE_FILE]
        sources = tables[SOURCE_FILE]

        search_by_id = self.unique_ids(searches, "search_id")
        source_by_id = self.unique_ids(sources, "source_id")
        screening_by_id = self.unique_ids(screenings, "record_id")
        self.unique_ids(evidence, "evidence_id")

        self.validate_searches(searches)
        source_paths = self.validate_sources(sources)
        included_sources = self.validate_screening(
            screenings,
            search_by_id,
            source_by_id,
            screening_by_id,
        )
        used_sources, usable_evidence = self.validate_evidence(
            evidence, source_by_id, included_sources
        )

        if included_sources and usable_evidence == 0:
            self.error(
                "missing_evidence",
                None,
                "one or more sources are included but no usable claim-source relationship exists",
                file=EVIDENCE_FILE,
            )
        for source_id in sorted(included_sources - used_sources):
            row = source_by_id.get(source_id)
            self.warning(
                "included_source_unused",
                row,
                f"included source {source_id!r} is not used by any valid claim-source relationship",
                file=SOURCE_FILE,
            )

        self.find_orphan_package_members(set(source_paths.values()))
        return sorted(self.issues, key=issue_sort_key)

    def validate_searches(self, rows: Iterable[TableRow]) -> None:
        for row in rows:
            self.require(row, "source")
            executed = self.require(row, "executed_date")
            self.require(row, "query")
            status = self.enum(row, "status", SEARCH_STATUSES)
            if executed is not None:
                try:
                    if ISO_DATE_RE.fullmatch(executed) is None:
                        raise ValueError
                    date.fromisoformat(executed)
                except ValueError:
                    self.error("invalid_date", row, "executed_date must use ISO YYYY-MM-DD")
            count_values: dict[str, int | None] = {}
            count_present: dict[str, bool] = {}
            for field in ("raw_count", "saved_count"):
                value = row.values[field].strip()
                count_present[field] = bool(value)
                if value and NONNEGATIVE_INTEGER_RE.fullmatch(value) is None:
                    self.error("invalid_count", row, f"{field} must be a non-negative integer or blank")
                    count_values[field] = None
                else:
                    count_values[field] = int(value) if value else None

            if status == "complete":
                raw_present = count_present["raw_count"]
                saved_present = count_present["saved_count"]
                if raw_present != saved_present:
                    self.error(
                        "incomplete_count_pair",
                        row,
                        "complete searches must provide both raw_count and saved_count, or leave both blank",
                    )
                elif not raw_present:
                    self.warning(
                        "complete_search_counts_missing",
                        row,
                        "complete search has no raw_count or saved_count; release completeness cannot be checked",
                    )
                else:
                    raw_count = count_values["raw_count"]
                    saved_count = count_values["saved_count"]
                    if (
                        raw_count is not None
                        and saved_count is not None
                        and saved_count > raw_count
                    ):
                        self.error(
                            "saved_count_exceeds_raw_count",
                            row,
                            f"saved_count {saved_count} exceeds raw_count {raw_count}",
                        )

    def validate_sources(self, rows: Iterable[TableRow]) -> dict[str, Path]:
        resolved_paths: dict[str, Path] = {}
        path_owner: dict[str, tuple[str, TableRow]] = {}
        for row in rows:
            source_id = row.values["source_id"].strip()
            self.require(row, "citation")
            self.enum(row, "evidence_role", SOURCE_ROLES)
            status = self.enum(row, "full_text_status", FULL_TEXT_STATUSES)
            raw_path = row.values["full_text_path"].strip()
            expected_hash = row.values["sha256"].strip()

            if status == "present":
                path = self.validate_relative_file_path(row, raw_path)
                if path is not None and source_id:
                    key = os.path.normcase(str(path))
                    if key in path_owner:
                        first_id, first_row = path_owner[key]
                        self.error(
                            "duplicate_full_text_path",
                            row,
                            f"full_text_path is already assigned to {first_id!r} at "
                            f"{first_row.file}:{first_row.line}",
                        )
                    else:
                        path_owner[key] = (source_id, row)
                    resolved_paths[source_id] = path
                if not expected_hash and self.strict_release:
                    self.error(
                        "missing_sha256",
                        row,
                        "sha256 is required for present full text in --strict-release mode",
                    )
                elif expected_hash:
                    if SHA256_RE.fullmatch(expected_hash) is None:
                        self.error("invalid_sha256", row, "sha256 must contain exactly 64 hexadecimal characters")
                    elif path is not None:
                        actual_hash = self.file_sha256(path, row)
                        if actual_hash is not None and actual_hash != expected_hash.lower():
                            self.error(
                                "sha256_mismatch",
                                row,
                                f"sha256 mismatch: expected {expected_hash.lower()}, found {actual_hash}",
                            )
            elif status in {"unavailable", "not_required"}:
                if raw_path:
                    self.error(
                        "unexpected_full_text_path",
                        row,
                        f"full_text_path must be blank when full_text_status is {status}",
                    )
                if expected_hash:
                    self.error(
                        "unexpected_sha256",
                        row,
                        f"sha256 must be blank when full_text_status is {status}",
                    )
        return resolved_paths

    def validate_screening(
        self,
        rows: Iterable[TableRow],
        search_by_id: dict[str, TableRow],
        source_by_id: dict[str, TableRow],
        screening_by_id: dict[str, TableRow],
    ) -> set[str]:
        decisions: list[ScreeningDecision] = []
        decision_by_id: dict[str, ScreeningDecision] = {}
        for row in rows:
            record_id = row.values["record_id"].strip() or None
            search_id = self.require(row, "search_id")
            source_id = row.values["source_id"].strip()
            self.require(row, "title")
            self.enum(row, "stage", SCREENING_STAGES)
            decision = self.enum(row, "decision", SCREENING_DECISIONS)
            decision_round_raw = self.require(row, "decision_round")
            decision_round: int | None = None
            if decision_round_raw is not None:
                if POSITIVE_INTEGER_RE.fullmatch(decision_round_raw) is None:
                    self.error(
                        "invalid_decision_round",
                        row,
                        "decision_round must be a positive integer",
                    )
                else:
                    decision_round = int(decision_round_raw)
            current_raw = self.enum(row, "current", BOOLEAN_VALUES)
            current = current_raw == "true" if current_raw is not None else None

            supersedes_raw = row.values["supersedes"].strip()
            supersedes: tuple[str, ...] = ()
            if supersedes_raw:
                raw_references = supersedes_raw.split(";")
                references = tuple(reference.strip() for reference in raw_references)
                if any(not reference for reference in references):
                    self.error(
                        "invalid_supersedes_list",
                        row,
                        "supersedes must be a semicolon-delimited list without empty references",
                    )
                elif len(set(references)) != len(references):
                    self.error(
                        "duplicate_supersedes_reference",
                        row,
                        "supersedes must not repeat a record_id",
                    )
                else:
                    supersedes = references

            if record_id is not None and ";" in record_id:
                self.error(
                    "invalid_record_id",
                    row,
                    "record_id must not contain ';' because it is a supersession delimiter",
                )

            if search_id is not None and search_id not in search_by_id:
                self.error("unresolved_search_id", row, f"search_id {search_id!r} is not in {SEARCH_FILE}")
            if source_id and source_id not in source_by_id:
                self.error("unresolved_source_id", row, f"source_id {source_id!r} is not in {SOURCE_FILE}")

            if decision == "include":
                if not source_id:
                    self.error("missing_source_id", row, "included records require source_id")
                role = self.enum(row, "evidence_role", SOURCE_ROLES)
                manifest_row = source_by_id.get(source_id)
                if role is not None and manifest_row is not None:
                    manifest_role = manifest_row.values["evidence_role"].strip()
                    if manifest_role and role != manifest_role:
                        self.error(
                            "source_role_mismatch",
                            row,
                            f"evidence_role {role!r} differs from source manifest role {manifest_role!r}",
                        )
            elif row.values["evidence_role"].strip():
                self.enum(row, "evidence_role", SOURCE_ROLES)

            if decision == "exclude" and not row.values["reason"].strip():
                self.error("missing_exclusion_reason", row, "excluded records require a specific reason")

            if (current is False or supersedes) and not source_id:
                self.error(
                    "missing_history_source_id",
                    row,
                    "versioned screening history requires source_id on every historical and superseding row",
                )

            parsed = ScreeningDecision(
                row=row,
                record_id=record_id,
                source_id=source_id,
                decision=decision,
                decision_round=decision_round,
                current=current,
                supersedes=supersedes,
            )
            decisions.append(parsed)
            if (
                record_id is not None
                and screening_by_id.get(record_id) is row
                and record_id not in decision_by_id
            ):
                decision_by_id[record_id] = parsed

        valid_edges: dict[str, tuple[str, ...]] = {}
        superseded_by: dict[str, ScreeningDecision] = {}
        for parsed in decisions:
            if parsed.record_id is None:
                continue
            valid_targets: list[str] = []
            for target_id in parsed.supersedes:
                target = decision_by_id.get(target_id)
                if target is None:
                    self.error(
                        "unresolved_supersedes_record_id",
                        parsed.row,
                        f"supersedes record_id {target_id!r} is not in {SCREENING_FILE}",
                    )
                    continue
                if target_id == parsed.record_id:
                    self.error(
                        "self_supersession",
                        parsed.row,
                        "a screening decision cannot supersede itself",
                    )
                    continue
                if not parsed.source_id or not target.source_id:
                    self.error(
                        "supersedes_missing_source_id",
                        parsed.row,
                        f"supersession of {target_id!r} requires source_id on both rows",
                    )
                    continue
                if parsed.source_id != target.source_id:
                    self.error(
                        "supersedes_source_mismatch",
                        parsed.row,
                        f"supersedes {target_id!r} from source_id {target.source_id!r}, not {parsed.source_id!r}",
                    )
                    continue
                if (
                    parsed.decision_round is not None
                    and target.decision_round is not None
                    and parsed.decision_round <= target.decision_round
                ):
                    self.error(
                        "invalid_supersession_order",
                        parsed.row,
                        f"decision_round must be greater than superseded row {target_id!r}",
                    )
                    continue
                if target.current is True:
                    self.error(
                        "supersedes_current_decision",
                        parsed.row,
                        f"superseded row {target_id!r} must have current=false",
                    )
                    continue
                first_successor = superseded_by.get(target_id)
                if first_successor is not None:
                    self.error(
                        "multiple_superseders",
                        parsed.row,
                        f"record_id {target_id!r} is already superseded by "
                        f"{first_successor.record_id!r} at {first_successor.row.file}:"
                        f"{first_successor.row.line}",
                    )
                    continue
                superseded_by[target_id] = parsed
                valid_targets.append(target_id)
            valid_edges[parsed.record_id] = tuple(valid_targets)

        self.validate_supersession_cycles(decision_by_id, valid_edges)

        source_decisions: dict[str, list[ScreeningDecision]] = {}
        for parsed in decisions:
            if parsed.source_id:
                source_decisions.setdefault(parsed.source_id, []).append(parsed)

        included: set[str] = set()
        for source_id, history in sorted(source_decisions.items()):
            current_rows = [parsed for parsed in history if parsed.current is True]
            if len(current_rows) > 1:
                rows_text = ", ".join(str(parsed.row.line) for parsed in current_rows)
                self.error(
                    "ambiguous_current_decision",
                    current_rows[1].row,
                    f"source_id {source_id!r} has multiple current decisions at rows {rows_text}",
                )
                continue
            if not current_rows:
                self.error(
                    "missing_current_decision",
                    history[0].row,
                    f"source_id {source_id!r} has screening history but no current=true decision",
                )
                continue

            current_row = current_rows[0]
            if current_row.decision == "include":
                included.add(source_id)

            reachable: set[str] = set()
            frontier = list(valid_edges.get(current_row.record_id or "", ()))
            while frontier:
                target_id = frontier.pop()
                if target_id in reachable:
                    continue
                reachable.add(target_id)
                frontier.extend(valid_edges.get(target_id, ()))
            for parsed in history:
                if (
                    parsed.current is False
                    and parsed.record_id is not None
                    and parsed.record_id not in reachable
                ):
                    self.error(
                        "unclosed_decision_history",
                        parsed.row,
                        f"historical record {parsed.record_id!r} is not in the supersession closure "
                        f"of current record {current_row.record_id!r}",
                    )
        return included

    def validate_supersession_cycles(
        self,
        decisions: dict[str, ScreeningDecision],
        edges: dict[str, tuple[str, ...]],
    ) -> None:
        state: dict[str, int] = {}
        reported: set[str] = set()

        def visit(record_id: str, trail: tuple[str, ...]) -> None:
            marker = state.get(record_id, 0)
            if marker == 2:
                return
            if marker == 1:
                if record_id not in reported:
                    cycle = trail[trail.index(record_id) :] + (record_id,)
                    row = decisions[record_id].row
                    self.error(
                        "supersession_cycle",
                        row,
                        "supersedes contains a cycle: " + " -> ".join(cycle),
                    )
                    reported.update(cycle)
                return
            state[record_id] = 1
            for target_id in edges.get(record_id, ()):
                visit(target_id, trail + (record_id,))
            state[record_id] = 2

        for record_id in sorted(decisions):
            visit(record_id, ())

    def validate_evidence(
        self,
        rows: Iterable[TableRow],
        source_by_id: dict[str, TableRow],
        included_sources: set[str],
    ) -> tuple[set[str], int]:
        used_sources: set[str] = set()
        claim_definitions: dict[str, tuple[str, str, TableRow]] = {}
        usable = 0

        for row in rows:
            claim_id = self.require(row, "claim_id")
            claim_text = self.require(row, "claim_text")
            claim_status = self.enum(row, "claim_status", CLAIM_STATUSES)
            source_id = self.require(row, "source_id")
            source_role = self.enum(row, "source_role", SOURCE_ROLES)
            locator = self.require(row, "locator")
            direction = self.enum(row, "direction", DIRECTIONS)
            strength = self.enum(row, "strength", STRENGTHS)
            intended_use = self.enum(row, "intended_use", INTENDED_USES)

            if claim_id is not None and claim_text is not None and claim_status is not None:
                definition = claim_definitions.get(claim_id)
                if definition is None:
                    claim_definitions[claim_id] = (claim_text, claim_status, row)
                elif (claim_text, claim_status) != definition[:2]:
                    self.error(
                        "inconsistent_claim_definition",
                        row,
                        f"claim_id {claim_id!r} differs from its definition at "
                        f"{definition[2].file}:{definition[2].line}",
                    )

            manifest_row = source_by_id.get(source_id or "")
            relationship_ok = all(
                value is not None
                for value in (
                    claim_id,
                    claim_text,
                    claim_status,
                    source_id,
                    source_role,
                    locator,
                    direction,
                    strength,
                    intended_use,
                )
            )
            if source_id is not None:
                if manifest_row is None:
                    self.error("unresolved_source_id", row, f"source_id {source_id!r} is not in {SOURCE_FILE}")
                    relationship_ok = False
                else:
                    manifest_role = manifest_row.values["evidence_role"].strip()
                    if source_role is not None and manifest_role and source_role != manifest_role:
                        self.error(
                            "source_role_mismatch",
                            row,
                            f"source_role {source_role!r} differs from source manifest role {manifest_role!r}",
                        )
                        relationship_ok = False
                if source_id not in included_sources:
                    self.error(
                        "source_not_included",
                        row,
                        f"source_id {source_id!r} has no include decision in {SCREENING_FILE}",
                    )
                    relationship_ok = False

            if relationship_ok and source_id is not None:
                used_sources.add(source_id)
                usable += 1
        return used_sources, usable

    def find_orphan_package_members(self, referenced: set[Path]) -> None:
        referenced_keys = {os.path.normcase(str(path.resolve())) for path in referenced}
        seen: set[str] = set()
        for dirname in ("full-text", "full_text"):
            package_dir = self.bundle / dirname
            if not package_dir.exists():
                continue
            if not package_dir.is_dir():
                self.warning(
                    "invalid_package_directory",
                    None,
                    f"{dirname} exists but is not a directory",
                    file=dirname,
                )
                continue
            try:
                resolved_dir = package_dir.resolve()
                common = os.path.commonpath((str(self.bundle), str(resolved_dir)))
            except (OSError, ValueError) as exc:
                self.read_error(
                    "package_scan_error",
                    dirname,
                    f"could not resolve package directory: {exc}",
                )
                continue
            if os.path.normcase(common) != os.path.normcase(str(self.bundle)):
                self.error(
                    "package_directory_escape",
                    None,
                    f"{dirname} resolves outside the bundle; directory was not scanned",
                    file=dirname,
                )
                continue
            try:
                members = sorted(
                    (path for path in package_dir.rglob("*") if path.is_file()),
                    key=lambda path: path.as_posix().casefold(),
                )
            except OSError as exc:
                self.read_error("package_scan_error", dirname, f"could not scan package directory: {exc}")
                continue
            for member in members:
                try:
                    key = os.path.normcase(str(member.resolve()))
                    display = member.relative_to(self.bundle).as_posix()
                except (OSError, ValueError) as exc:
                    self.warning(
                        "orphan_package_member",
                        None,
                        f"could not resolve package member {member.name!r}: {exc}",
                        file=dirname,
                    )
                    continue
                if key not in referenced_keys and key not in seen:
                    self.warning(
                        "orphan_package_member",
                        None,
                        f"package file is not referenced by {SOURCE_FILE}: {display}",
                        file=display,
                    )
                seen.add(key)


def issue_sort_key(issue: Issue) -> tuple[int, str, int, str, str]:
    return (
        0 if issue.severity == "error" else 1,
        issue.file.casefold(),
        issue.row if issue.row is not None else 0,
        issue.code,
        issue.message,
    )


def render_text(bundle: Path, issues: Sequence[Issue]) -> str:
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    status = "FAIL" if errors else "PASS"
    lines = [f"{status} bundle={bundle}", f"errors={errors} warnings={warnings}"]
    for issue in issues:
        location = issue.file or "."
        if issue.row is not None:
            location = f"{location}:{issue.row}"
        lines.append(f"{issue.severity.upper()} {issue.code} {location} - {issue.message}")
    return "\n".join(lines)


def render_json(bundle: Path, issues: Sequence[Issue]) -> str:
    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    payload = {
        "bundle": str(bundle),
        "status": "error" if errors else "ok",
        "error_count": errors,
        "warning_count": warnings,
        "issues": [asdict(issue) for issue in issues],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate deterministic relationships and package integrity in a review bundle."
    )
    parser.add_argument("--bundle", required=True, type=Path, help="review bundle directory")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="report format (default: text)",
    )
    parser.add_argument(
        "--strict-release",
        action="store_true",
        help=(
            "require hashes for present full text and promote every open warning "
            "to an error"
        ),
    )
    return parser


def configure_utf8_output() -> None:
    """Make machine-readable output deterministic on Windows and POSIX."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def main(argv: Sequence[str] | None = None) -> int:
    configure_utf8_output()
    args = build_parser().parse_args(argv)
    try:
        bundle = args.bundle.resolve()
    except OSError as exc:
        issue = Issue("error", "invalid_bundle", ".", None, f"could not resolve --bundle: {exc}")
        output = render_json(args.bundle, [issue]) if args.format == "json" else render_text(args.bundle, [issue])
        print(output)
        return 2
    if not bundle.exists() or not bundle.is_dir():
        issue = Issue("error", "invalid_bundle", ".", None, "--bundle must name an existing directory")
        output = render_json(bundle, [issue]) if args.format == "json" else render_text(bundle, [issue])
        print(output)
        return 2

    validator = BundleValidator(bundle, strict_release=args.strict_release)
    issues = validator.validate()
    output = render_json(bundle, issues) if args.format == "json" else render_text(bundle, issues)
    print(output)
    if validator.read_failed:
        return 2
    if any(issue.severity == "error" for issue in issues):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
