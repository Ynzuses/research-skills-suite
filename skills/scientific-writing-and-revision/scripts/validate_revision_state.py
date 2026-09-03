#!/usr/bin/env python3
"""Validate the structural closure of a scientific revision-state record."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
ABSOLUTE_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|/)")
SURFACE_STATES = {"current", "stale", "missing", "frozen"}
EPISTEMIC_STATES = {
    "source-fact",
    "synthesis",
    "conditional-inference",
    "approved-decision",
    "open-option",
    "result",
    "hypothesis",
}
JUDGMENTS = {"correct", "partly-correct", "preference-dependent", "unsupported"}


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    location: str
    message: str


class StrictJSONError(ValueError):
    """Raised when input uses JSON constructs forbidden by the contract."""


def configure_standard_streams() -> None:
    """Make CLI output strict UTF-8 regardless of the Windows code page."""
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
        description="Validate revision-state JSON without editing documents or judging prose."
    )
    parser.add_argument("state_file", type=Path)
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    return parser.parse_args()


def add(findings: list[Finding], code: str, location: str, message: str) -> None:
    findings.append(Finding("error", code, location, message))


def required_text(value: Any, location: str, findings: list[Finding]) -> bool:
    if not isinstance(value, str) or not value.strip():
        add(findings, "required_text", location, "must be a non-empty string")
        return False
    if PLACEHOLDER_RE.search(value):
        add(findings, "placeholder", location, "contains an unresolved placeholder")
        return False
    return True


def portable_locator(value: Any, location: str, findings: list[Finding]) -> None:
    if required_text(value, location, findings) and isinstance(value, str):
        normalized = value.replace("\\", "/")
        if ABSOLUTE_RE.match(value):
            add(findings, "absolute_path", location, "must not embed an absolute local path")
        if ".." in normalized.split("/"):
            add(findings, "path_escape", location, "must not contain parent traversal")


def unique_id(
    value: Any, location: str, seen: set[str], findings: list[Finding]
) -> str | None:
    if not required_text(value, location, findings):
        return None
    assert isinstance(value, str)
    if value in seen:
        add(findings, "duplicate_id", location, f"duplicates {value!r}")
    seen.add(value)
    return value


def validate(data: Any) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(data, dict):
        return [Finding("error", "root_type", "$", "root must be a JSON object")]
    if data.get("schema_version") != "1.1":
        add(
            findings,
            "schema_version",
            "schema_version",
            "expected '1.1'; migrate older records by preserving them and adding an explicit extensions object",
        )
    required_text(data.get("document_id"), "document_id", findings)
    required_text(data.get("document_type"), "document_type", findings)

    purpose = data.get("purpose_contract")
    if not isinstance(purpose, dict):
        add(findings, "required_object", "purpose_contract", "must be an object")
    else:
        for key in ("objective", "intended_contribution", "current_document_role"):
            required_text(purpose.get(key), f"purpose_contract.{key}", findings)
        for key in ("supporting_assets", "deferred_deliverables", "disallowed_substitutes"):
            if not isinstance(purpose.get(key), list):
                add(findings, "required_list", f"purpose_contract.{key}", "must be a list")

    evidence = data.get("evidence_snapshot")
    if not isinstance(evidence, dict):
        add(findings, "required_object", "evidence_snapshot", "must be an object")
    else:
        required_text(evidence.get("id"), "evidence_snapshot.id", findings)
        portable_locator(evidence.get("location"), "evidence_snapshot.location", findings)

    surfaces = data.get("surfaces")
    surface_ids: set[str] = set()
    if not isinstance(surfaces, list) or not surfaces:
        add(findings, "required_list", "surfaces", "must contain at least one surface")
    else:
        for index, surface in enumerate(surfaces):
            loc = f"surfaces[{index}]"
            if not isinstance(surface, dict):
                add(findings, "invalid_surface", loc, "must be an object")
                continue
            unique_id(surface.get("surface_id"), f"{loc}.surface_id", surface_ids, findings)
            required_text(surface.get("role"), f"{loc}.role", findings)
            portable_locator(surface.get("location"), f"{loc}.location", findings)
            status = surface.get("status")
            if not isinstance(status, str) or status not in SURFACE_STATES:
                add(
                    findings,
                    "invalid_surface_state",
                    f"{loc}.status",
                    f"expected one of {sorted(SURFACE_STATES)}",
                )

    claims = data.get("claims")
    claim_ids: set[str] = set()
    if not isinstance(claims, list):
        add(findings, "required_list", "claims", "must be a list")
    else:
        for index, claim in enumerate(claims):
            loc = f"claims[{index}]"
            if not isinstance(claim, dict):
                add(findings, "invalid_claim", loc, "must be an object")
                continue
            unique_id(claim.get("claim_id"), f"{loc}.claim_id", claim_ids, findings)
            epistemic_status = claim.get("epistemic_status")
            if not isinstance(epistemic_status, str) or epistemic_status not in EPISTEMIC_STATES:
                add(
                    findings,
                    "invalid_epistemic_status",
                    f"{loc}.epistemic_status",
                    f"expected one of {sorted(EPISTEMIC_STATES)}",
                )
            required_text(claim.get("evidence_locator"), f"{loc}.evidence_locator", findings)
            refs = claim.get("surface_ids")
            if not isinstance(refs, list) or not refs:
                add(findings, "required_list", f"{loc}.surface_ids", "must not be empty")
            else:
                for ref_index, ref in enumerate(refs):
                    if not required_text(ref, f"{loc}.surface_ids[{ref_index}]", findings):
                        continue
                    assert isinstance(ref, str)
                    if ref not in surface_ids:
                        add(
                            findings,
                            "unknown_surface",
                            f"{loc}.surface_ids",
                            f"references {ref!r}",
                        )

    decisions = data.get("feedback_decisions")
    feedback_ids: set[str] = set()
    if not isinstance(decisions, list):
        add(findings, "required_list", "feedback_decisions", "must be a list")
    else:
        for index, decision in enumerate(decisions):
            loc = f"feedback_decisions[{index}]"
            if not isinstance(decision, dict):
                add(findings, "invalid_feedback", loc, "must be an object")
                continue
            unique_id(decision.get("feedback_id"), f"{loc}.feedback_id", feedback_ids, findings)
            judgment = decision.get("judgment")
            if not isinstance(judgment, str) or judgment not in JUDGMENTS:
                add(
                    findings,
                    "invalid_judgment",
                    f"{loc}.judgment",
                    f"expected one of {sorted(JUDGMENTS)}",
                )
            for key in ("reason", "local_repair", "global_pattern", "verification"):
                required_text(decision.get(key), f"{loc}.{key}", findings)
            refs = decision.get("affected_surface_ids")
            if not isinstance(refs, list) or not refs:
                add(findings, "required_list", f"{loc}.affected_surface_ids", "must not be empty")
            else:
                for ref_index, ref in enumerate(refs):
                    if not required_text(
                        ref, f"{loc}.affected_surface_ids[{ref_index}]", findings
                    ):
                        continue
                    assert isinstance(ref, str)
                    if ref not in surface_ids:
                        add(
                            findings,
                            "unknown_surface",
                            f"{loc}.affected_surface_ids",
                            f"references {ref!r}",
                        )

    if not isinstance(data.get("unresolved_gaps"), list):
        add(findings, "required_list", "unresolved_gaps", "must be a list")
    required_text(data.get("next_action"), "next_action", findings)
    if not isinstance(data.get("extensions"), dict):
        add(
            findings,
            "required_object",
            "extensions",
            "must be an object reserved for project-specific additions",
        )
    return sorted(findings, key=lambda item: (item.code, item.location, item.message))


def emit(findings: list[Finding], output_format: str, path: Path) -> None:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "file": path.as_posix(),
                    "errors": len(findings),
                    "findings": [asdict(item) for item in findings],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return
    for item in findings:
        print(f"ERROR {item.code} {item.location}: {item.message}")
    verdict = "FAIL" if findings else "STRUCTURAL PASS"
    print(f"RESULT: {verdict} ({len(findings)} error(s))")


def main() -> int:
    configure_standard_streams()
    args = parse_args()
    try:
        data = load_strict_json(args.state_file)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: cannot read revision state: {exc}", file=sys.stderr)
        return 2
    findings = validate(data)
    emit(findings, args.output_format, args.state_file)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
