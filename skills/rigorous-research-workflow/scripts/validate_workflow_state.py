#!/usr/bin/env python3
"""Validate a persisted Rigorous Research Workflow state record.

The validator is dependency-free and read-only. It checks structural closure and
artifact identity fields; it does not judge scientific correctness or approve a
stage transition.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any


STATES = {
    "scoped",
    "evidence-ready",
    "content-ready",
    "delivery-candidate",
    "submitted/frozen",
    "revision-round",
    "public-release",
}
PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
INVALIDATION_STATES = {"open", "resolved", "waived"}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    location: str
    message: str


class StrictJSONError(ValueError):
    """Raised when input uses JSON constructs forbidden by the contract."""


def configure_standard_streams() -> None:
    """Make machine-readable output independent of the Windows console code page."""
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
        description="Validate a workflow-state JSON file without modifying it."
    )
    parser.add_argument("state_file", type=Path, help="Path to workflow-state JSON.")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
        help="Stable output format (default: text).",
    )
    return parser.parse_args()


def add(
    findings: list[Finding], severity: str, code: str, location: str, message: str
) -> None:
    findings.append(Finding(severity, code, location, message))


def nonempty_string(
    value: Any, location: str, findings: list[Finding], *, placeholders: bool = False
) -> bool:
    if not isinstance(value, str) or not value.strip():
        add(findings, "error", "required_string", location, "must be a non-empty string")
        return False
    if not placeholders and PLACEHOLDER_RE.search(value):
        add(findings, "error", "placeholder", location, "contains an unresolved placeholder")
        return False
    return True


def validate_location(value: Any, location: str, findings: list[Finding]) -> None:
    if not nonempty_string(value, location, findings):
        return
    assert isinstance(value, str)
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if WINDOWS_ABSOLUTE_RE.match(value) or path.is_absolute():
        add(findings, "error", "absolute_path", location, "must be portable, not absolute")
    if ".." in path.parts:
        add(findings, "error", "path_escape", location, "must not contain parent traversal")


def validate_unique_string_list(
    value: Any,
    location: str,
    findings: list[Finding],
    *,
    required: bool = False,
) -> list[str]:
    if not isinstance(value, list) or (required and not value):
        message = "must be a non-empty list" if required else "must be a list"
        add(findings, "error", "required_list", location, message)
        return []
    result: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_location = f"{location}[{index}]"
        if not nonempty_string(item, item_location, findings):
            continue
        assert isinstance(item, str)
        if item in seen:
            add(findings, "error", "duplicate_list_item", item_location, repr(item))
            continue
        seen.add(item)
        result.append(item)
    return result


def validate_authority(
    name: str,
    authorities: dict[str, Any],
    findings: list[Finding],
    *,
    exact_file: bool = False,
) -> None:
    location = f"authorities.{name}"
    value = authorities.get(name)
    if not isinstance(value, dict):
        add(findings, "error", "missing_authority", location, "must be an object")
        return
    nonempty_string(value.get("id"), f"{location}.id", findings)
    validate_location(value.get("location"), f"{location}.location", findings)
    if exact_file:
        digest = value.get("sha256")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            add(
                findings,
                "error",
                "missing_exact_identity",
                f"{location}.sha256",
                "must be a 64-character SHA-256 for an exact delivery artifact",
            )


def validate_invalidations(
    data: dict[str, Any],
    known_target_ids: set[str],
    findings: list[Finding],
) -> tuple[set[str], set[str]]:
    records = data.get("invalidations")
    if not isinstance(records, list):
        add(findings, "error", "required_list", "invalidations", "must be a list")
        return set(), set()

    invalidation_ids: set[str] = set()
    open_ids: set[str] = set()
    for index, item in enumerate(records):
        location = f"invalidations[{index}]"
        if not isinstance(item, dict):
            add(findings, "error", "invalid_invalidation", location, "must be an object")
            continue

        invalidation_id = item.get("invalidation_id")
        if nonempty_string(invalidation_id, f"{location}.invalidation_id", findings):
            assert isinstance(invalidation_id, str)
            if invalidation_id in invalidation_ids:
                add(
                    findings,
                    "error",
                    "duplicate_invalidation_id",
                    f"{location}.invalidation_id",
                    repr(invalidation_id),
                )
            invalidation_ids.add(invalidation_id)

        target_id = item.get("target_id")
        if nonempty_string(target_id, f"{location}.target_id", findings):
            assert isinstance(target_id, str)
            if target_id not in known_target_ids:
                add(
                    findings,
                    "error",
                    "unknown_invalidation_target",
                    f"{location}.target_id",
                    f"{target_id!r} is not a current authority or required output",
                )

        for field in ("trigger_event_id", "reason"):
            nonempty_string(item.get(field), f"{location}.{field}", findings)
        validate_location(item.get("trigger_evidence"), f"{location}.trigger_evidence", findings)

        previous = item.get("previous_identity")
        if not isinstance(previous, dict):
            add(
                findings,
                "error",
                "required_object",
                f"{location}.previous_identity",
                "must identify the invalidated baseline",
            )
        else:
            nonempty_string(
                previous.get("identity"),
                f"{location}.previous_identity.identity",
                findings,
            )
            digest = previous.get("sha256")
            if digest is not None and (
                not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None
            ):
                add(
                    findings,
                    "error",
                    "invalid_sha256",
                    f"{location}.previous_identity.sha256",
                    "must be null or a 64-character SHA-256",
                )

        critical = item.get("critical")
        if not isinstance(critical, bool):
            add(
                findings,
                "error",
                "required_boolean",
                f"{location}.critical",
                "must be true or false",
            )

        status = item.get("status")
        if not isinstance(status, str) or status not in INVALIDATION_STATES:
            add(findings, "error", "invalid_invalidation_state", f"{location}.status", repr(status))
            status = None
        elif status == "open" and isinstance(invalidation_id, str):
            open_ids.add(invalidation_id)

        required_rechecks = validate_unique_string_list(
            item.get("required_rechecks"),
            f"{location}.required_rechecks",
            findings,
            required=True,
        )

        resolution = item.get("resolution")
        waiver = item.get("waiver")
        if status == "open":
            if resolution is not None or waiver is not None:
                add(
                    findings,
                    "error",
                    "open_invalidation_has_disposition",
                    location,
                    "open invalidations require null resolution and waiver",
                )
        elif status == "resolved":
            if waiver is not None:
                add(
                    findings,
                    "error",
                    "resolved_with_waiver",
                    f"{location}.waiver",
                    "resolved invalidations cannot also be waived",
                )
            if not isinstance(resolution, dict):
                add(
                    findings,
                    "error",
                    "missing_resolution",
                    f"{location}.resolution",
                    "resolved invalidations require a resolution object",
                )
            else:
                replacement_id = resolution.get("replacement_target_id")
                if nonempty_string(
                    replacement_id,
                    f"{location}.resolution.replacement_target_id",
                    findings,
                ):
                    assert isinstance(replacement_id, str)
                    if replacement_id not in known_target_ids:
                        add(
                            findings,
                            "error",
                            "unknown_replacement_target",
                            f"{location}.resolution.replacement_target_id",
                            repr(replacement_id),
                        )
                nonempty_string(
                    resolution.get("new_identity"),
                    f"{location}.resolution.new_identity",
                    findings,
                )
                completed = validate_unique_string_list(
                    resolution.get("completed_rechecks"),
                    f"{location}.resolution.completed_rechecks",
                    findings,
                    required=True,
                )
                missing = sorted(set(required_rechecks) - set(completed))
                for check_id in missing:
                    add(
                        findings,
                        "error",
                        "missing_required_recheck",
                        f"{location}.resolution.completed_rechecks",
                        repr(check_id),
                    )
                evidence = validate_unique_string_list(
                    resolution.get("evidence"),
                    f"{location}.resolution.evidence",
                    findings,
                    required=True,
                )
                for evidence_index, evidence_item in enumerate(evidence):
                    validate_location(
                        evidence_item,
                        f"{location}.resolution.evidence[{evidence_index}]",
                        findings,
                    )
                for field in ("resolved_by", "resolved_at"):
                    nonempty_string(
                        resolution.get(field),
                        f"{location}.resolution.{field}",
                        findings,
                    )
        elif status == "waived":
            if resolution is not None:
                add(
                    findings,
                    "error",
                    "waived_with_resolution",
                    f"{location}.resolution",
                    "waived invalidations cannot also be resolved",
                )
            if critical is True:
                add(
                    findings,
                    "error",
                    "critical_invalidation_waived",
                    f"{location}.critical",
                    "critical invalidations must be resolved, not waived",
                )
            if not isinstance(waiver, dict):
                add(
                    findings,
                    "error",
                    "missing_waiver",
                    f"{location}.waiver",
                    "waived invalidations require a waiver object",
                )
            else:
                for field in ("reason", "authorized_by", "decided_at", "residual_risk"):
                    nonempty_string(waiver.get(field), f"{location}.waiver.{field}", findings)
                validate_location(
                    waiver.get("evidence"),
                    f"{location}.waiver.evidence",
                    findings,
                )

        if not isinstance(item.get("extensions"), dict):
            add(
                findings,
                "error",
                "required_object",
                f"{location}.extensions",
                "must be an object reserved for project-specific additions",
            )

    return invalidation_ids, open_ids


def validate_transition_chain(
    data: dict[str, Any],
    findings: list[Finding],
    invalidation_ids: set[str],
) -> set[str]:
    transitions = data.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        add(findings, "error", "required_list", "transitions", "must be a non-empty list")
        return set()

    seen: set[str] = set()
    referenced_invalidations: set[str] = set()
    prior_to: str | None = None
    for index, item in enumerate(transitions):
        location = f"transitions[{index}]"
        if not isinstance(item, dict):
            add(findings, "error", "invalid_transition", location, "must be an object")
            continue
        transition_id = item.get("transition_id")
        if nonempty_string(transition_id, f"{location}.transition_id", findings):
            assert isinstance(transition_id, str)
            if transition_id in seen:
                add(
                    findings,
                    "error",
                    "duplicate_transition_id",
                    f"{location}.transition_id",
                    f"duplicates {transition_id!r}",
                )
            seen.add(transition_id)
        from_state = item.get("from")
        to_state = item.get("to")
        if from_state is not None and (
            not isinstance(from_state, str) or from_state not in STATES
        ):
            add(findings, "error", "invalid_state", f"{location}.from", repr(from_state))
        if not isinstance(to_state, str) or to_state not in STATES:
            add(findings, "error", "invalid_state", f"{location}.to", repr(to_state))
        if index == 0:
            if from_state is not None:
                add(
                    findings,
                    "warning",
                    "initial_from_state",
                    f"{location}.from",
                    "first transition normally starts from null",
                )
        elif from_state != prior_to:
            add(
                findings,
                "error",
                "broken_transition_chain",
                f"{location}.from",
                f"expected {prior_to!r}, found {from_state!r}",
            )
        prior_to = to_state if isinstance(to_state, str) and to_state in STATES else prior_to
        for field in ("date", "owner"):
            nonempty_string(item.get(field), f"{location}.{field}", findings)
        evidence = item.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            add(
                findings,
                "error",
                "missing_transition_evidence",
                f"{location}.evidence",
                "must contain at least one authority or locator",
            )
        elif any(not isinstance(entry, str) or not entry.strip() for entry in evidence):
            add(
                findings,
                "error",
                "invalid_transition_evidence",
                f"{location}.evidence",
                "entries must be non-empty strings",
            )
        invalidated = validate_unique_string_list(
            item.get("invalidated"),
            f"{location}.invalidated",
            findings,
        )
        for invalidation_id in invalidated:
            if invalidation_id not in invalidation_ids:
                add(
                    findings,
                    "error",
                    "unknown_transition_invalidation",
                    f"{location}.invalidated",
                    repr(invalidation_id),
                )
            else:
                referenced_invalidations.add(invalidation_id)

    current = data.get("current_state")
    if prior_to in STATES and current != prior_to:
        add(
            findings,
            "error",
            "current_state_mismatch",
            "current_state",
            f"last transition ends at {prior_to!r}",
        )
    return referenced_invalidations


def validate(data: Any) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(data, dict):
        return [Finding("error", "root_type", "$", "root must be a JSON object")]

    if data.get("schema_version") != "2.0":
        add(
            findings,
            "error",
            "schema_version",
            "schema_version",
            "expected '2.0'; migrate older invalidation records explicitly",
        )
    nonempty_string(data.get("workflow_id"), "workflow_id", findings)
    state = data.get("current_state")
    if not isinstance(state, str) or state not in STATES:
        add(findings, "error", "invalid_state", "current_state", repr(state))

    purpose = data.get("purpose_contract")
    required_output_ids: set[str] = set()
    if not isinstance(purpose, dict):
        add(findings, "error", "required_object", "purpose_contract", "must be an object")
    else:
        for field in ("id", "objective", "intended_contribution", "unit_and_scale"):
            nonempty_string(purpose.get(field), f"purpose_contract.{field}", findings)
        required_output_ids.update(
            validate_unique_string_list(
                purpose.get("required_outputs"),
                "purpose_contract.required_outputs",
                findings,
                required=True,
            )
        )

    authorities = data.get("authorities")
    if not isinstance(authorities, dict):
        add(findings, "error", "required_object", "authorities", "must be an object")
        authorities = {}
    validate_authority("design", authorities, findings)
    authority_ids: set[str] = set()
    for authority_name, authority in authorities.items():
        if not isinstance(authority, dict):
            continue
        authority_id = authority.get("id")
        if not isinstance(authority_id, str) or not authority_id.strip():
            continue
        if authority_id in authority_ids:
            add(
                findings,
                "error",
                "duplicate_authority_id",
                f"authorities.{authority_name}.id",
                repr(authority_id),
            )
        authority_ids.add(authority_id)

    if isinstance(state, str) and state in {
        "evidence-ready",
        "content-ready",
        "delivery-candidate",
        "submitted/frozen",
        "revision-round",
        "public-release",
    }:
        if not isinstance(authorities.get("evidence_snapshot"), dict) and not isinstance(
            authorities.get("analysis_snapshot"), dict
        ):
            add(
                findings,
                "error",
                "missing_stage_authority",
                "authorities",
                "state requires an evidence_snapshot or analysis_snapshot",
            )
        else:
            for name in ("evidence_snapshot", "analysis_snapshot"):
                if isinstance(authorities.get(name), dict):
                    validate_authority(name, authorities, findings)

    if isinstance(state, str) and state in {
        "content-ready",
        "delivery-candidate",
        "submitted/frozen",
        "revision-round",
        "public-release",
    }:
        validate_authority("content_snapshot", authorities, findings)

    if isinstance(state, str) and state in {
        "delivery-candidate",
        "submitted/frozen",
        "revision-round",
        "public-release",
    }:
        validate_authority(
            "delivery_artifact",
            authorities,
            findings,
            exact_file=state in {"submitted/frozen", "revision-round", "public-release"},
        )

    nonempty_string(data.get("privacy_boundary"), "privacy_boundary", findings)
    invalidation_ids, open_invalidation_ids = validate_invalidations(
        data,
        authority_ids | required_output_ids,
        findings,
    )
    if not isinstance(data.get("blockers"), list):
        add(findings, "error", "required_list", "blockers", "must be a list")
    if state == "revision-round" and not open_invalidation_ids:
        add(
            findings,
            "error",
            "revision_without_invalidation",
            "invalidations",
            "revision-round must retain at least one open invalidation",
        )
    if state != "revision-round" and open_invalidation_ids:
        add(
            findings,
            "error",
            "open_invalidation_outside_revision",
            "current_state",
            "open invalidations require revision-round; resolve them before advancing",
        )

    next_action = data.get("next_action")
    if not isinstance(next_action, dict):
        add(findings, "error", "required_object", "next_action", "must be an object")
    else:
        for field in ("action", "input", "expected_output", "acceptance"):
            nonempty_string(next_action.get(field), f"next_action.{field}", findings)

    referenced_invalidations = validate_transition_chain(data, findings, invalidation_ids)
    for invalidation_id in sorted(invalidation_ids - referenced_invalidations):
        add(
            findings,
            "error",
            "unrecorded_invalidation_transition",
            "transitions",
            f"{invalidation_id!r} is not cited by any transition.invalidated list",
        )
    if not isinstance(data.get("extensions"), dict):
        add(
            findings,
            "error",
            "required_object",
            "extensions",
            "must be an object reserved for project-specific additions",
        )
    return sorted(findings, key=lambda item: (item.severity, item.code, item.location, item.message))


def emit(findings: list[Finding], output_format: str, state_file: Path) -> None:
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    if output_format == "json":
        payload = {
            "file": state_file.as_posix(),
            "errors": errors,
            "warnings": warnings,
            "findings": [asdict(item) for item in findings],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    for item in findings:
        print(f"{item.severity.upper()} {item.code} {item.location}: {item.message}")
    verdict = "FAIL" if errors else "STRUCTURAL PASS"
    print(f"RESULT: {verdict} ({errors} error(s), {warnings} warning(s))")


def main() -> int:
    configure_standard_streams()
    args = parse_args()
    try:
        data = load_strict_json(args.state_file)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: cannot read workflow state: {exc}", file=sys.stderr)
        return 2
    findings = validate(data)
    emit(findings, args.output_format, args.state_file)
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
