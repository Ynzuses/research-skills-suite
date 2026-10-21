#!/usr/bin/env python3
"""Validate computational run state, checkpoint closure, and local file hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any


PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")
RUN_STATES = {"planned", "running", "complete", "failed", "partial", "stale"}
TASK_STATES = {"planned", "running", "complete", "failed", "skipped"}
OUTPUT_STATES = {"missing", "partial", "produced", "verified-zero", "stale", "failed"}
CHECKPOINT_STATES = {"pending", "passed", "failed", "stale"}


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
        description="Validate a run-manifest JSON without modifying workflow artifacts."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    parser.add_argument(
        "--strict-complete",
        action="store_true",
        help=(
            "require a complete run, locally verifiable completion markers, "
            "and closed skip/output identities"
        ),
    )
    return parser.parse_args()


def add(
    findings: list[Finding], severity: str, code: str, location: str, message: str
) -> None:
    findings.append(Finding(severity, code, location, message))


def required_text(value: Any, location: str, findings: list[Finding]) -> bool:
    if not isinstance(value, str) or not value.strip():
        add(findings, "error", "required_text", location, "must be a non-empty string")
        return False
    if PLACEHOLDER_RE.search(value):
        add(findings, "error", "placeholder", location, "contains an unresolved placeholder")
        return False
    return True


def unique_id(
    value: Any, location: str, seen: set[str], findings: list[Finding]
) -> str | None:
    if not required_text(value, location, findings):
        return None
    assert isinstance(value, str)
    if value in seen:
        add(findings, "error", "duplicate_id", location, f"duplicates {value!r}")
    seen.add(value)
    return value


def safe_local_path(
    base: Path,
    value: Any,
    location: str,
    findings: list[Finding],
    *,
    external_is_error: bool = False,
) -> Path | None:
    if not required_text(value, location, findings):
        return None
    assert isinstance(value, str)
    if value.startswith("external:"):
        add(
            findings,
            "error" if external_is_error else "warning",
            "unverifiable_external_artifact" if external_is_error else "external_artifact",
            location,
            (
                "strict completion requires a locally verifiable artifact"
                if external_is_error
                else "external identity cannot be checked by this local validator"
            ),
        )
        return None
    normalized = value.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if WINDOWS_ABSOLUTE_RE.match(value) or pure.is_absolute() or ".." in pure.parts:
        add(
            findings,
            "error",
            "unsafe_path",
            location,
            "must be relative to the manifest or use an external: symbolic locator",
        )
        return None
    target = (base / Path(*pure.parts)).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError:
        add(findings, "error", "path_escape", location, "resolves outside manifest directory")
        return None
    return target


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate(
    data: Any,
    manifest_path: Path,
    *,
    strict_complete: bool = False,
) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(data, dict):
        return [Finding("error", "root_type", "$", "root must be a JSON object")]
    if data.get("schema_version") != "1.0":
        add(findings, "error", "schema_version", "schema_version", "expected '1.0'")
    for field in ("run_id", "stage_id", "scientific_question"):
        required_text(data.get(field), field, findings)
    run_state = data.get("state")
    if not isinstance(run_state, str) or run_state not in RUN_STATES:
        add(findings, "error", "invalid_run_state", "state", f"expected one of {sorted(RUN_STATES)}")
    elif strict_complete and run_state != "complete":
        add(
            findings,
            "error",
            "strict_complete_state",
            "state",
            "--strict-complete requires state 'complete'",
        )

    inputs = data.get("inputs")
    input_ids: set[str] = set()
    if not isinstance(inputs, list) or not inputs:
        add(findings, "error", "required_list", "inputs", "must contain at least one input")
    else:
        for index, item in enumerate(inputs):
            loc = f"inputs[{index}]"
            if not isinstance(item, dict):
                add(findings, "error", "invalid_input", loc, "must be an object")
                continue
            unique_id(item.get("input_id"), f"{loc}.input_id", input_ids, findings)
            for field in ("role", "identity", "verification"):
                required_text(item.get(field), f"{loc}.{field}", findings)
            target = safe_local_path(manifest_path.parent, item.get("path"), f"{loc}.path", findings)
            if target is not None and not target.exists():
                add(findings, "error", "missing_input", f"{loc}.path", target.as_posix())

    code = data.get("code")
    if not isinstance(code, dict):
        add(findings, "error", "required_object", "code", "must be an object")
    else:
        entrypoint_value = code.get("entrypoint")
        entrypoint = safe_local_path(
            manifest_path.parent, entrypoint_value, "code.entrypoint", findings
        )
        if run_state == "complete":
            if entrypoint is not None and not entrypoint.is_file():
                add(
                    findings,
                    "error",
                    "missing_entrypoint",
                    "code.entrypoint",
                    entrypoint.as_posix(),
                )
            elif (
                entrypoint is None
                and isinstance(entrypoint_value, str)
                and entrypoint_value.startswith("external:")
            ):
                add(
                    findings,
                    "error",
                    "unverifiable_entrypoint",
                    "code.entrypoint",
                    "complete runs require a locally verifiable entrypoint",
                )
        for field in ("version", "parameters"):
            required_text(code.get(field), f"code.{field}", findings)

    environment = data.get("environment")
    if not isinstance(environment, dict):
        add(findings, "error", "required_object", "environment", "must be an object")
    else:
        for field in ("identity", "activation", "verification"):
            required_text(environment.get(field), f"environment.{field}", findings)

    partition = data.get("partition_contract")
    expected_tasks: list[str] = []
    if not isinstance(partition, dict):
        add(findings, "error", "required_object", "partition_contract", "must be an object")
    else:
        for field in ("unit", "retry_rule", "overwrite_rule"):
            required_text(partition.get(field), f"partition_contract.{field}", findings)
        raw_expected = partition.get("expected_task_ids")
        if not isinstance(raw_expected, list) or not raw_expected:
            add(
                findings,
                "error",
                "required_list",
                "partition_contract.expected_task_ids",
                "must not be empty",
            )
        else:
            for index, value in enumerate(raw_expected):
                if required_text(value, f"partition_contract.expected_task_ids[{index}]", findings):
                    assert isinstance(value, str)
                    expected_tasks.append(value)
            if len(set(expected_tasks)) != len(expected_tasks):
                add(
                    findings,
                    "error",
                    "duplicate_task_id",
                    "partition_contract.expected_task_ids",
                    "contains duplicates",
                )

    outputs = data.get("outputs")
    output_ids: set[str] = set()
    output_states: dict[str, str] = {}
    output_fingerprints: dict[str, str] = {}
    output_completion_critical: dict[str, bool] = {}
    output_locations: dict[str, str] = {}
    if not isinstance(outputs, list) or not outputs:
        add(findings, "error", "required_list", "outputs", "must contain at least one output")
    else:
        for index, output in enumerate(outputs):
            loc = f"outputs[{index}]"
            if not isinstance(output, dict):
                add(findings, "error", "invalid_output", loc, "must be an object")
                continue
            output_id = unique_id(output.get("output_id"), f"{loc}.output_id", output_ids, findings)
            if output_id is not None:
                output_locations[output_id] = loc
            required_text(output.get("role"), f"{loc}.role", findings)
            completion_critical = output.get("completion_critical")
            if completion_critical is not None and not isinstance(completion_critical, bool):
                add(
                    findings,
                    "error",
                    "required_boolean",
                    f"{loc}.completion_critical",
                    "must be true, false, or null while the run is not finalized",
                )
            if strict_complete and not isinstance(completion_critical, bool):
                add(
                    findings,
                    "error",
                    "missing_completion_critical_decision",
                    f"{loc}.completion_critical",
                    "--strict-complete requires an explicit true or false decision",
                )
            if output_id is not None and isinstance(completion_critical, bool):
                output_completion_critical[output_id] = completion_critical
            state = output.get("semantic_state")
            if not isinstance(state, str) or state not in OUTPUT_STATES:
                add(
                    findings,
                    "error",
                    "invalid_output_state",
                    f"{loc}.semantic_state",
                    f"expected one of {sorted(OUTPUT_STATES)}",
                )
            elif output_id is not None:
                output_states[output_id] = state
            for field in ("schema", "verification"):
                required_text(output.get(field), f"{loc}.{field}", findings)
            upstream_fingerprint = output.get("upstream_fingerprint")
            if required_text(
                upstream_fingerprint,
                f"{loc}.upstream_fingerprint",
                findings,
            ) and output_id is not None:
                assert isinstance(upstream_fingerprint, str)
                output_fingerprints[output_id] = upstream_fingerprint
            target = safe_local_path(
                manifest_path.parent,
                output.get("path"),
                f"{loc}.path",
                findings,
                external_is_error=(
                    strict_complete
                    and completion_critical is True
                    and isinstance(state, str)
                    and state in {"produced", "verified-zero"}
                ),
            )
            recorded_hash = output.get("sha256")
            if isinstance(state, str) and state in {"produced", "verified-zero"}:
                if not isinstance(recorded_hash, str) or not SHA256_RE.fullmatch(recorded_hash):
                    add(
                        findings,
                        "error",
                        "missing_output_identity",
                        f"{loc}.sha256",
                        "produced and verified-zero outputs require a SHA-256",
                    )
                count = output.get("row_or_record_count")
                if state == "produced" and count is not None and (
                    isinstance(count, bool) or not isinstance(count, int) or count < 0
                ):
                    add(
                        findings,
                        "error",
                        "invalid_produced_count",
                        f"{loc}.row_or_record_count",
                        "produced outputs require a non-negative integer count or null",
                    )
                if state == "verified-zero" and (
                    isinstance(count, bool) or not isinstance(count, int) or count != 0
                ):
                    add(
                        findings,
                        "error",
                        "invalid_zero_state",
                        f"{loc}.row_or_record_count",
                        "verified-zero requires an explicit count of 0",
                    )
                if target is not None:
                    if not target.is_file():
                        add(findings, "error", "missing_output", f"{loc}.path", target.as_posix())
                    else:
                        try:
                            actual = file_hash(target)
                        except OSError as exc:
                            add(findings, "error", "unreadable_output", f"{loc}.path", str(exc))
                        else:
                            if isinstance(recorded_hash, str) and actual != recorded_hash.lower():
                                add(
                                    findings,
                                    "error",
                                    "hash_mismatch",
                                    f"{loc}.sha256",
                                    f"recorded {recorded_hash.lower()}, actual {actual}",
                                )
            elif recorded_hash is not None and state == "missing":
                add(
                    findings,
                    "error",
                    "missing_with_hash",
                    f"{loc}.sha256",
                    "a missing output cannot claim a current file hash",
                )

    tasks = data.get("tasks")
    task_ids: set[str] = set()
    task_states: dict[str, str] = {}
    referenced_output_ids: set[str] = set()
    if not isinstance(tasks, list) or not tasks:
        add(findings, "error", "required_list", "tasks", "must contain at least one task")
    else:
        for index, task in enumerate(tasks):
            loc = f"tasks[{index}]"
            if not isinstance(task, dict):
                add(findings, "error", "invalid_task", loc, "must be an object")
                continue
            task_id = unique_id(task.get("task_id"), f"{loc}.task_id", task_ids, findings)
            state = task.get("state")
            if not isinstance(state, str) or state not in TASK_STATES:
                add(
                    findings,
                    "error",
                    "invalid_task_state",
                    f"{loc}.state",
                    f"expected one of {sorted(TASK_STATES)}",
                )
            elif task_id is not None:
                task_states[task_id] = state
            if state == "failed" and (strict_complete or run_state == "complete"):
                add(
                    findings,
                    "error",
                    "failed_task_in_complete_run",
                    f"{loc}.state",
                    "a complete or strict-complete run cannot contain a failed task",
                )
            attempt = task.get("attempt")
            if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 0:
                add(findings, "error", "invalid_attempt", f"{loc}.attempt", "must be >= 0")
            elif state == "complete" and attempt < 1:
                add(
                    findings,
                    "error",
                    "invalid_complete_attempt",
                    f"{loc}.attempt",
                    "complete tasks require an execution attempt of at least 1",
                )
            exit_code = task.get("exit_code")
            if state == "complete" and (
                isinstance(exit_code, bool)
                or not isinstance(exit_code, int)
                or exit_code != 0
            ):
                add(
                    findings,
                    "error",
                    "complete_without_success_exit",
                    f"{loc}.exit_code",
                    "complete tasks require exit_code 0",
                )
            if state == "skipped" and exit_code is not None:
                add(
                    findings,
                    "error",
                    "skipped_with_exit_code",
                    f"{loc}.exit_code",
                    "skipped tasks keep exit_code null; prior attempts belong in failure history",
                )
            refs = task.get("output_ids")
            resolved_refs: list[str] = []
            if not isinstance(refs, list) or not refs:
                add(findings, "error", "required_list", f"{loc}.output_ids", "must not be empty")
            else:
                for ref_index, ref in enumerate(refs):
                    if not required_text(ref, f"{loc}.output_ids[{ref_index}]", findings):
                        continue
                    assert isinstance(ref, str)
                    if ref not in output_ids:
                        add(findings, "error", "unknown_output", f"{loc}.output_ids", repr(ref))
                    else:
                        resolved_refs.append(ref)
                        referenced_output_ids.add(ref)
            required_text(task.get("evidence"), f"{loc}.evidence", findings)

            success_marker = task.get("success_marker")
            skip_record = task.get("skip_record")
            if state == "complete":
                if success_marker is None:
                    add(
                        findings,
                        "error",
                        "missing_success_marker",
                        f"{loc}.success_marker",
                        "complete tasks require a non-empty, locally verifiable success marker",
                    )
                else:
                    marker = safe_local_path(
                        manifest_path.parent,
                        success_marker,
                        f"{loc}.success_marker",
                        findings,
                        external_is_error=True,
                    )
                    if marker is not None and not marker.is_file():
                        add(
                            findings,
                            "error",
                            "missing_success_marker_file",
                            f"{loc}.success_marker",
                            marker.as_posix(),
                        )
                    elif marker is not None:
                        try:
                            with marker.open("rb") as handle:
                                first_byte = handle.read(1)
                        except OSError as exc:
                            add(
                                findings,
                                "error",
                                "unreadable_success_marker",
                                f"{loc}.success_marker",
                                str(exc),
                            )
                        else:
                            if not first_byte:
                                add(
                                    findings,
                                    "error",
                                    "empty_success_marker",
                                    f"{loc}.success_marker",
                                    "success marker exists but is empty",
                                )
                if skip_record is not None:
                    add(
                        findings,
                        "error",
                        "unexpected_skip_record",
                        f"{loc}.skip_record",
                        "only skipped tasks may contain a skip_record",
                    )
            elif state == "skipped":
                if success_marker is not None:
                    add(
                        findings,
                        "error",
                        "skipped_with_success_marker",
                        f"{loc}.success_marker",
                        "skipped tasks must not claim an execution success marker",
                    )
                if not isinstance(skip_record, dict):
                    add(
                        findings,
                        "error",
                        "missing_skip_record",
                        f"{loc}.skip_record",
                        "skipped tasks require a structured skip_record",
                    )
                else:
                    for field in ("reason", "upstream_fingerprint", "verification"):
                        required_text(skip_record.get(field), f"{loc}.skip_record.{field}", findings)
                    skip_fingerprint = skip_record.get("upstream_fingerprint")
                    if isinstance(skip_fingerprint, str) and skip_fingerprint.strip():
                        for output_id in resolved_refs:
                            if output_fingerprints.get(output_id) != skip_fingerprint:
                                add(
                                    findings,
                                    "error",
                                    "skip_upstream_identity_mismatch",
                                    f"{loc}.skip_record.upstream_fingerprint",
                                    f"does not match output {output_id!r}",
                                )
                    for output_id in resolved_refs:
                        if output_states.get(output_id) not in {"produced", "verified-zero"}:
                            add(
                                findings,
                                "error",
                                "skipped_without_current_output",
                                f"{loc}.output_ids",
                                f"skipped task output {output_id!r} is not produced or verified-zero",
                            )
            else:
                if success_marker is not None:
                    add(
                        findings,
                        "error",
                        "unexpected_success_marker",
                        f"{loc}.success_marker",
                        "only complete tasks may contain a success marker",
                    )
                if skip_record is not None:
                    add(
                        findings,
                        "error",
                        "unexpected_skip_record",
                        f"{loc}.skip_record",
                        "only skipped tasks may contain a skip_record",
                    )

    missing_tasks = sorted(set(expected_tasks) - task_ids)
    unexpected_tasks = sorted(task_ids - set(expected_tasks))
    for task_id in missing_tasks:
        add(findings, "error", "missing_task", "tasks", repr(task_id))
    for task_id in unexpected_tasks:
        add(
            findings,
            "error" if strict_complete else "warning",
            "unexpected_task",
            "tasks",
            (
                f"{task_id!r} is not declared by partition_contract.expected_task_ids; "
                "strict completion requires an exact task set"
                if strict_complete
                else repr(task_id)
            ),
        )

    if strict_complete:
        for output_id, completion_critical in output_completion_critical.items():
            if completion_critical and output_id not in referenced_output_ids:
                add(
                    findings,
                    "error",
                    "unreferenced_completion_critical_output",
                    f"{output_locations[output_id]}.completion_critical",
                    f"completion-critical output {output_id!r} is not referenced by any task",
                )

    checkpoints = data.get("checkpoints")
    checkpoint_ids: set[str] = set()
    checkpoint_by_task: dict[str, str] = {}
    checkpoint_tasks_seen: set[str] = set()
    if not isinstance(checkpoints, list):
        add(findings, "error", "required_list", "checkpoints", "must be a list")
        checkpoints = []
    for index, checkpoint in enumerate(checkpoints):
        loc = f"checkpoints[{index}]"
        if not isinstance(checkpoint, dict):
            add(findings, "error", "invalid_checkpoint", loc, "must be an object")
            continue
        unique_id(
            checkpoint.get("checkpoint_id"), f"{loc}.checkpoint_id", checkpoint_ids, findings
        )
        task_id = checkpoint.get("task_id")
        if required_text(task_id, f"{loc}.task_id", findings):
            assert isinstance(task_id, str)
            if task_id not in task_ids:
                add(findings, "error", "unknown_task", f"{loc}.task_id", repr(task_id))
            if task_id in checkpoint_tasks_seen:
                add(
                    findings,
                    "error",
                    "duplicate_task_checkpoint",
                    f"{loc}.task_id",
                    f"task {task_id!r} has more than one completion checkpoint",
                )
            checkpoint_tasks_seen.add(task_id)
        status = checkpoint.get("status")
        if not isinstance(status, str) or status not in CHECKPOINT_STATES:
            add(
                findings,
                "error",
                "invalid_checkpoint_state",
                f"{loc}.status",
                f"expected one of {sorted(CHECKPOINT_STATES)}",
            )
        elif isinstance(task_id, str):
            checkpoint_by_task[task_id] = status
        for field in ("completion_contract", "evidence"):
            required_text(checkpoint.get(field), f"{loc}.{field}", findings)

    if run_state == "complete":
        for task_id in expected_tasks:
            if task_states.get(task_id) not in {"complete", "skipped"}:
                add(
                    findings,
                    "error",
                    "incomplete_task",
                    "state",
                    f"task {task_id!r} is not complete or validly skipped",
                )
            if checkpoint_by_task.get(task_id) != "passed":
                add(
                    findings,
                    "error",
                    "checkpoint_not_passed",
                    "state",
                    f"task {task_id!r} lacks a passed completion checkpoint",
                )
        for output_id, state in output_states.items():
            if state not in {"produced", "verified-zero"}:
                add(
                    findings,
                    "error",
                    "incomplete_output",
                    "state",
                    f"output {output_id!r} is {state!r}",
                )

    for field in ("failures_and_fallbacks",):
        if not isinstance(data.get(field), list):
            add(findings, "error", "required_list", field, "must be a list")
    required_text(data.get("privacy_and_release"), "privacy_and_release", findings)
    required_text(data.get("next_action"), "next_action", findings)
    if not isinstance(data.get("extensions"), dict):
        add(findings, "error", "required_object", "extensions", "must be an object")
    return sorted(findings, key=lambda item: (item.severity, item.code, item.location, item.message))


def emit(
    findings: list[Finding],
    output_format: str,
    manifest: Path,
    *,
    strict_complete: bool,
    run_state: str | None,
) -> None:
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    completion_validated = strict_complete and run_state == "complete" and errors == 0
    if errors:
        verdict = "fail"
    elif completion_validated:
        verdict = "complete_pass"
    else:
        verdict = "structural_pass"
    if output_format == "json":
        print(
            json.dumps(
                {
                    "manifest": manifest.as_posix(),
                    "errors": errors,
                    "warnings": warnings,
                    "strict_complete": strict_complete,
                    "run_state": run_state,
                    "validation_mode": "strict-complete" if strict_complete else "structural",
                    "completion_validated": completion_validated,
                    "verdict": verdict,
                    "findings": [asdict(item) for item in findings],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return
    for item in findings:
        print(f"{item.severity.upper()} {item.code} {item.location}: {item.message}")
    if errors:
        label = "FAIL"
        suffix = ""
    elif completion_validated:
        label = "COMPLETE PASS"
        suffix = ""
    else:
        label = "STRUCTURAL PASS"
        suffix = (
            "; completion was not validated; rerun with --strict-complete"
            if run_state == "complete"
            else ""
        )
    print(f"RESULT: {label} ({errors} error(s), {warnings} warning(s){suffix})")


def main() -> int:
    configure_standard_streams()
    args = parse_args()
    manifest = args.manifest.resolve()
    try:
        data = load_strict_json(manifest)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: cannot read run manifest: {exc}", file=sys.stderr)
        return 2
    findings = validate(data, manifest, strict_complete=args.strict_complete)
    run_state = data.get("state") if isinstance(data, dict) and isinstance(data.get("state"), str) else None
    emit(
        findings,
        args.output_format,
        manifest,
        strict_complete=args.strict_complete,
        run_state=run_state,
    )
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
