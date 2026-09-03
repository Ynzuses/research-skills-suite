#!/usr/bin/env python3
"""Structurally verify a delivery record and its local, hash-bound evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "2.0"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
STATES = {"draft", "candidate", "revision", "final", "submitted", "frozen", "release", "public-release"}
VALIDATION_STATES = {"passed", "failed", "unavailable", "not-applicable"}
RELEASE_STATES = {"final", "submitted", "frozen", "release", "public-release"}
EVIDENCE_KINDS = {"file", "manual", "external"}
EVIDENCE_MODES = {"file", "non-file"}
NON_WAIVABLE_RELEASE_GATES = {"rendered", "delivery-package"}
BASE_RELEASE_GATES = {"content", "delivery-package"}
MEDIA_RELEASE_GATES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {"package", "rendered"},
    "application/pdf": {"rendered"},
}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    location: str
    message: str


class StrictJSONError(ValueError):
    pass


def configure_standard_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def reject_nonfinite_number(value: str) -> None:
    raise StrictJSONError(f"non-finite number {value!r} is not permitted")


def load_strict_json(path: Path) -> Any:
    return json.loads(
        path.read_text(encoding="utf-8", errors="strict"),
        object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_nonfinite_number,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Structurally verify DELIVERY_RECORD 2.0 and local hashes; this does not independently validate delivery content."
    )
    parser.add_argument("record", type=Path)
    parser.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    return parser.parse_args()


def add(findings: list[Finding], severity: str, code: str, location: str, message: str) -> None:
    findings.append(Finding(severity, code, location, message))


def required_text(value: Any, location: str, findings: list[Finding]) -> bool:
    if not isinstance(value, str) or not value.strip():
        add(findings, "error", "required_text", location, "must be a non-empty string")
        return False
    if PLACEHOLDER_RE.search(value):
        add(findings, "error", "placeholder", location, "contains an unresolved placeholder")
        return False
    return True


def extensions(value: Any, location: str, findings: list[Finding]) -> None:
    if not isinstance(value, dict):
        add(findings, "error", "required_object", location, "must be an object")


def timestamp(value: Any, location: str, findings: list[Finding]) -> bool:
    if not required_text(value, location, findings):
        return False
    assert isinstance(value, str)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        add(findings, "error", "invalid_timestamp", location, "must be ISO-8601")
        return False
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        add(findings, "error", "missing_timezone", location, "must include a timezone")
        return False
    return True


def resolve_relative(base: Path, value: Any, location: str, findings: list[Finding]) -> Path | None:
    if not required_text(value, location, findings):
        return None
    assert isinstance(value, str)
    pure = PurePosixPath(value.replace("\\", "/"))
    if WINDOWS_ABSOLUTE_RE.match(value) or pure.is_absolute() or ".." in pure.parts:
        add(findings, "error", "unsafe_path", location, "must be relative and contained by the record directory")
        return None
    base_resolved = base.resolve()
    candidate = base_resolved.joinpath(*pure.parts)
    try:
        candidate.resolve(strict=False).relative_to(base_resolved)
    except (OSError, ValueError):
        add(findings, "error", "path_escape", location, "resolves outside record directory")
        return None
    return candidate


def is_reparse_point(path: Path) -> bool:
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def require_regular_file(path: Path, location: str, missing_code: str, findings: list[Finding]) -> bool:
    try:
        metadata = path.lstat()
    except OSError as exc:
        add(findings, "error", missing_code, location, str(exc))
        return False
    if path.is_symlink() or is_reparse_point(path) or not stat.S_ISREG(metadata.st_mode):
        add(findings, "error", "non_regular_file", location, "must be a local ordinary file, not a link, reparse point, or directory")
        return False
    return True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_hashed_file(
    base: Path,
    record: Any,
    location: str,
    findings: list[Finding],
    *,
    missing_code: str,
) -> str | None:
    if not isinstance(record, dict):
        add(findings, "error", "required_object", location, "must be an object")
        return None
    target = resolve_relative(base, record.get("path"), f"{location}.path", findings)
    recorded_hash = record.get("sha256")
    if not isinstance(recorded_hash, str) or not SHA256_RE.fullmatch(recorded_hash):
        add(findings, "error", "invalid_sha256", f"{location}.sha256", "must be a 64-character SHA-256")
    extensions(record.get("extensions"), f"{location}.extensions", findings)
    if target is None or not require_regular_file(target, f"{location}.path", missing_code, findings):
        return None
    try:
        actual = sha256(target)
    except OSError as exc:
        add(findings, "error", "unreadable_file", f"{location}.path", str(exc))
        return None
    if isinstance(recorded_hash, str) and SHA256_RE.fullmatch(recorded_hash) and actual != recorded_hash.lower():
        add(findings, "error", "hash_mismatch", f"{location}.sha256", f"recorded {recorded_hash.lower()}, actual {actual}")
    return actual


def validate(data: Any, record_path: Path) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(data, dict):
        return [Finding("error", "root_type", "$", "root must be a JSON object")]
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        if version == "1.0":
            message = "schema 1.0 cannot prove gate closure; migrate to 2.0 with per-artifact required_gates, structured hash-bound evidence, and extensions"
        else:
            message = f"unsupported schema {version!r}; expected {SCHEMA_VERSION!r}; use a documented migrator before validation"
        return [Finding("error", "schema_version_migration", "schema_version", message)]

    required_text(data.get("delivery_id"), "delivery_id", findings)
    extensions(data.get("extensions"), "extensions", findings)
    state = data.get("state")
    if not isinstance(state, str) or state not in STATES:
        add(findings, "error", "invalid_state", "state", f"expected one of {sorted(STATES)}")
    release_state = isinstance(state, str) and state in RELEASE_STATES
    for field in ("content_authority", "format_authority", "synchronization_direction"):
        required_text(data.get(field), field, findings)

    artifacts = data.get("artifacts")
    artifact_map: dict[str, dict[str, Any]] = {}
    actual_hashes: dict[str, str] = {}
    gate_contracts: dict[str, dict[str, dict[str, Any]]] = {}
    if not isinstance(artifacts, list) or not artifacts:
        add(findings, "error", "required_list", "artifacts", "must contain at least one artifact")
        artifacts = []
    for index, artifact in enumerate(artifacts):
        loc = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            add(findings, "error", "invalid_artifact", loc, "must be an object")
            continue
        artifact_id = artifact.get("artifact_id")
        valid_id = required_text(artifact_id, f"{loc}.artifact_id", findings)
        if valid_id:
            assert isinstance(artifact_id, str)
            if artifact_id in artifact_map:
                add(findings, "error", "duplicate_artifact_id", f"{loc}.artifact_id", repr(artifact_id))
            else:
                artifact_map[artifact_id] = artifact
        required_text(artifact.get("role"), f"{loc}.role", findings)
        required_text(artifact.get("media_type"), f"{loc}.media_type", findings)
        actual = verify_hashed_file(record_path.parent, artifact, loc, findings, missing_code="missing_artifact")
        if valid_id and actual is not None:
            actual_hashes[artifact_id] = actual

        required_gates = artifact.get("required_gates")
        contracts: dict[str, dict[str, Any]] = {}
        if not isinstance(required_gates, list):
            add(findings, "error", "required_list", f"{loc}.required_gates", "must be a list")
            required_gates = []
        for gate_index, contract in enumerate(required_gates):
            gate_loc = f"{loc}.required_gates[{gate_index}]"
            if not isinstance(contract, dict):
                add(findings, "error", "invalid_gate_contract", gate_loc, "must be an object")
                continue
            gate = contract.get("gate")
            if not required_text(gate, f"{gate_loc}.gate", findings):
                continue
            assert isinstance(gate, str)
            if gate in contracts:
                add(findings, "error", "duplicate_required_gate", f"{gate_loc}.gate", repr(gate))
            mode = contract.get("evidence_mode")
            if mode not in EVIDENCE_MODES:
                add(findings, "error", "invalid_evidence_mode", f"{gate_loc}.evidence_mode", f"expected one of {sorted(EVIDENCE_MODES)}")
            extensions(contract.get("extensions"), f"{gate_loc}.extensions", findings)
            contracts[gate] = contract
        if valid_id:
            gate_contracts[artifact_id] = contracts

    members_value = data.get("delivery_members")
    if not isinstance(members_value, list) or not members_value:
        add(findings, "error", "required_list", "delivery_members", "must not be empty")
        members_value = []
    members: list[str] = []
    seen_members: set[str] = set()
    for index, artifact_id in enumerate(members_value):
        if not required_text(artifact_id, f"delivery_members[{index}]", findings):
            continue
        assert isinstance(artifact_id, str)
        if artifact_id in seen_members:
            add(findings, "error", "duplicate_member", f"delivery_members[{index}]", repr(artifact_id))
        seen_members.add(artifact_id)
        members.append(artifact_id)
        if artifact_id not in artifact_map:
            add(findings, "error", "unknown_artifact", f"delivery_members[{index}]", repr(artifact_id))

    if release_state:
        for artifact_id in members:
            artifact = artifact_map.get(artifact_id, {})
            media_type = artifact.get("media_type")
            expected = set(BASE_RELEASE_GATES)
            if isinstance(media_type, str):
                expected.update(MEDIA_RELEASE_GATES.get(media_type, set()))
            for gate in sorted(expected - set(gate_contracts.get(artifact_id, {}))):
                add(findings, "error", "missing_required_gate_contract", f"artifacts[{artifact_id!r}].required_gates", f"release member with media type {media_type!r} must require gate {gate!r}")

    validations = data.get("validations")
    if not isinstance(validations, list):
        add(findings, "error", "required_list", "validations", "must be a list")
        validations = []
    validation_map: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for index, validation in enumerate(validations):
        loc = f"validations[{index}]"
        if not isinstance(validation, dict):
            add(findings, "error", "invalid_validation", loc, "must be an object")
            continue
        extensions(validation.get("extensions"), f"{loc}.extensions", findings)
        gate = validation.get("gate")
        artifact_id = validation.get("artifact_id")
        valid_gate = required_text(gate, f"{loc}.gate", findings)
        valid_artifact_id = required_text(artifact_id, f"{loc}.artifact_id", findings)
        if valid_artifact_id and artifact_id not in artifact_map:
            add(findings, "error", "unknown_artifact", f"{loc}.artifact_id", repr(artifact_id))
        if valid_gate and valid_artifact_id:
            assert isinstance(gate, str) and isinstance(artifact_id, str)
            validation_map.setdefault((artifact_id, gate), []).append(validation)

        status_value = validation.get("status")
        if not isinstance(status_value, str) or status_value not in VALIDATION_STATES:
            add(findings, "error", "invalid_validation_status", f"{loc}.status", f"expected one of {sorted(VALIDATION_STATES)}")
        validation_hash = validation.get("artifact_sha256")
        hash_is_current = False
        if not isinstance(validation_hash, str) or not SHA256_RE.fullmatch(validation_hash):
            add(findings, "error", "invalid_sha256", f"{loc}.artifact_sha256", "must be a 64-character SHA-256")
        elif isinstance(artifact_id, str) and artifact_id in actual_hashes:
            if validation_hash.lower() != actual_hashes[artifact_id]:
                add(findings, "error", "stale_validation", f"{loc}.artifact_sha256", "validation is not bound to the current artifact")
            else:
                hash_is_current = True
        if status_value != "not-applicable":
            timestamp(validation.get("performed_at"), f"{loc}.performed_at", findings)
        required_text(validation.get("limitations"), f"{loc}.limitations", findings)

        contract = None
        if isinstance(artifact_id, str) and isinstance(gate, str):
            contract = gate_contracts.get(artifact_id, {}).get(gate)
        evidence = validation.get("evidence")
        if status_value == "passed":
            if not isinstance(evidence, dict):
                add(findings, "error", "required_object", f"{loc}.evidence", "passed validation requires structured evidence")
            else:
                kind = evidence.get("kind")
                if kind == "file":
                    verify_hashed_file(record_path.parent, evidence, f"{loc}.evidence", findings, missing_code="missing_evidence_file")
                elif kind in {"manual", "external"}:
                    extensions(evidence.get("extensions"), f"{loc}.evidence.extensions", findings)
                    required_text(evidence.get("description"), f"{loc}.evidence.description", findings)
                    required_text(evidence.get("source"), f"{loc}.evidence.source", findings)
                    declared_non_file = isinstance(contract, dict) and contract.get("evidence_mode") == "non-file"
                    if release_state and not declared_non_file:
                        add(findings, "error", "undeclared_non_file_evidence", f"{loc}.evidence.kind", "release evidence must follow the required-gate contract")
                    if release_state and isinstance(artifact_id, str) and artifact_id in members and contract is not None:
                        add(findings, "error", "release_requires_file_evidence", f"{loc}.evidence.kind", "manual or external evidence cannot close a required final/release gate; capture it in a local hash-bound evidence file")
                else:
                    add(findings, "error", "invalid_evidence_kind", f"{loc}.evidence.kind", f"expected one of {sorted(EVIDENCE_KINDS)}")
        elif evidence is not None:
            if not isinstance(evidence, dict):
                add(findings, "error", "required_object", f"{loc}.evidence", "must be null or structured evidence")
            else:
                kind = evidence.get("kind")
                if kind == "file":
                    verify_hashed_file(record_path.parent, evidence, f"{loc}.evidence", findings, missing_code="missing_evidence_file")
                elif kind in {"manual", "external"}:
                    extensions(evidence.get("extensions"), f"{loc}.evidence.extensions", findings)
                    required_text(evidence.get("description"), f"{loc}.evidence.description", findings)
                    required_text(evidence.get("source"), f"{loc}.evidence.source", findings)
                else:
                    add(findings, "error", "invalid_evidence_kind", f"{loc}.evidence.kind", f"expected one of {sorted(EVIDENCE_KINDS)}")

        decision = validation.get("not_applicable")
        if status_value == "not-applicable":
            if not isinstance(decision, dict):
                add(findings, "error", "missing_not_applicable_decision", f"{loc}.not_applicable", "must record reason, authorized_by, and decided_at")
            else:
                required_text(decision.get("reason"), f"{loc}.not_applicable.reason", findings)
                required_text(decision.get("authorized_by"), f"{loc}.not_applicable.authorized_by", findings)
                timestamp(decision.get("decided_at"), f"{loc}.not_applicable.decided_at", findings)
                extensions(decision.get("extensions"), f"{loc}.not_applicable.extensions", findings)
            if release_state and gate in NON_WAIVABLE_RELEASE_GATES:
                add(findings, "error", "non_waivable_release_gate", f"{loc}.status", f"required release gate {gate!r} cannot be replaced by not-applicable")
        elif decision is not None:
            add(findings, "error", "unexpected_not_applicable_decision", f"{loc}.not_applicable", "is only allowed when status is 'not-applicable'")

        if release_state and isinstance(artifact_id, str) and artifact_id in members and contract is not None:
            if not hash_is_current:
                add(findings, "error", "required_gate_not_current", f"{loc}.artifact_sha256", "required release gate must bind the current artifact hash")
            if status_value not in {"passed", "not-applicable"}:
                add(findings, "error", "unclosed_required_gate", f"{loc}.status", "required release gate must pass or carry an authorized not-applicable decision")

    for (artifact_id, gate), records in validation_map.items():
        if len(records) > 1:
            severity = "error" if release_state and artifact_id in members else "warning"
            add(findings, severity, "duplicate_gate_validation", f"validations[{artifact_id!r},{gate!r}]", "must resolve to one current validation before release")

    if release_state:
        for artifact_id in members:
            for gate in gate_contracts.get(artifact_id, {}):
                records = validation_map.get((artifact_id, gate), [])
                if not records:
                    add(findings, "error", "missing_required_gate_validation", f"artifacts[{artifact_id!r}].required_gates[{gate!r}]", "has no validation record")
                elif len(records) == 1 and records[0].get("status") not in {"passed", "not-applicable"}:
                    add(findings, "error", "unclosed_required_gate", f"artifacts[{artifact_id!r}].required_gates[{gate!r}]", "must pass or carry an authorized not-applicable decision")

    if isinstance(state, str) and state in {"submitted", "frozen"}:
        required_text(data.get("submitted_baseline_id"), "submitted_baseline_id", findings)
        for artifact_id in members:
            artifact = artifact_map.get(artifact_id)
            if isinstance(artifact, dict) and artifact.get("frozen") is not True:
                add(findings, "error", "unfrozen_delivery_member", f"artifacts[{artifact_id!r}].frozen", "submitted/frozen delivery members must be marked frozen")
    for field in ("invalidated_checks", "unresolved_risks"):
        if not isinstance(data.get(field), list):
            add(findings, "error", "required_list", field, "must be a list")
    required_text(data.get("next_action"), "next_action", findings)
    return sorted(findings, key=lambda item: (item.severity, item.code, item.location, item.message))


def emit(findings: list[Finding], output_format: str, record: Path) -> None:
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    if output_format == "json":
        print(json.dumps({
            "record": record.as_posix(),
            "validation_mode": "structural",
            "verdict": "fail" if errors else "structural_pass",
            "delivery_completion_validated": False,
            "errors": errors,
            "warnings": warnings,
            "findings": [asdict(item) for item in findings],
        }, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for item in findings:
        print(f"{item.severity.upper()} {item.code} {item.location}: {item.message}")
    if errors:
        print(f"RESULT: FAIL ({errors} error(s), {warnings} warning(s))")
    else:
        print(f"RESULT: STRUCTURAL PASS ({errors} error(s), {warnings} warning(s); delivery completion was not independently validated)")


def main() -> int:
    configure_standard_streams()
    args = parse_args()
    record = args.record.resolve()
    try:
        data = load_strict_json(record)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: cannot read delivery record: {exc}", file=sys.stderr)
        return 2
    findings = validate(data, record)
    emit(findings, args.output_format, record)
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
