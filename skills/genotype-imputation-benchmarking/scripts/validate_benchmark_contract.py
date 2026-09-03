#!/usr/bin/env python3
"""Validate structural closure of a genotype-imputation benchmark contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
INTERFACES = {
    "hard-genotype",
    "genotype-likelihood",
    "read-data",
    "allele-count",
    "array-genotype",
    "pedigree",
    "low-coverage-haplotype",
    "other",
}
ROLES = {"candidate", "baseline", "diagnostic", "ablation"}
INPUT_ROLES = {
    "target-observation",
    "reference-panel",
    "genetic-map",
    "pedigree",
    "metadata",
    "other",
}
INPUT_TYPES = {
    "hard-genotype",
    "genotype-likelihood",
    "read-data",
    "allele-count",
    "array-genotype",
    "reference-haplotype",
    "genetic-map",
    "pedigree",
    "metadata",
    "other",
}
LEAKAGE_STATES = {"controlled", "open", "not-applicable"}
EVALUATION_SETS = {"native", "common"}
METRIC_EVALUATION_SETS = {"native", "common", "both"}
CONFIRMATORY_LOCK_STATES = {"open", "frozen"}
INPUT_STATES = {"open", "verified", "retired"}
PILOT_STATES = {"planned", "running", "passed", "failed", "stale"}
PILOT_VALIDATION_STATES = {"pending", "passed", "failed"}
DOWNSTREAM_APPLICABILITY = {"open", "required", "not-applicable"}
DOWNSTREAM_ROLES = {"confirmatory", "exploratory", "diagnostic"}
DOWNSTREAM_STATES = {"open", "ready", "completed", "failed"}
SCHEMA_VERSION = "2.0"


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
        description="Validate a benchmark-contract JSON without running a benchmark."
    )
    parser.add_argument("contract", type=Path)
    parser.add_argument(
        "--format", choices=("text", "json"), default="text", dest="output_format"
    )
    parser.add_argument(
        "--strict-confirmatory",
        action="store_true",
        help=(
            "require verified truth-free inputs, current passed pilots, closed "
            "downstream and leakage declarations, and a fingerprint-matched freeze"
        ),
    )
    return parser.parse_args()


def add(
    findings: list[Finding], severity: str, code: str, location: str, message: str
) -> None:
    findings.append(Finding(severity, code, location, message))


def text(value: Any, location: str, findings: list[Finding]) -> bool:
    if not isinstance(value, str) or not value.strip():
        add(findings, "error", "required_text", location, "must be a non-empty string")
        return False
    if PLACEHOLDER_RE.search(value):
        add(findings, "error", "placeholder", location, "contains an unresolved placeholder")
        return False
    return True


def string_list(
    value: Any,
    location: str,
    findings: list[Finding],
    *,
    nonempty: bool = True,
) -> list[str]:
    if not isinstance(value, list) or (nonempty and not value):
        add(
            findings,
            "error",
            "required_list",
            location,
            "must be a non-empty list" if nonempty else "must be a list",
        )
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if text(item, f"{location}[{index}]", findings):
            assert isinstance(item, str)
            result.append(item)
    if len(set(result)) != len(result):
        add(findings, "error", "duplicate_list_value", location, "contains duplicates")
    return result


def object_list(
    value: Any,
    location: str,
    findings: list[Finding],
    *,
    nonempty: bool = True,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (nonempty and not value):
        message = "must contain at least one object" if nonempty else "must be a list"
        add(findings, "error", "required_list", location, message)
        return []
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            add(findings, "error", "invalid_object", f"{location}[{index}]", "must be an object")
        else:
            result.append(item)
    return result


def collect_ids(
    records: list[dict[str, Any]],
    field: str,
    prefix: str,
    findings: list[Finding],
) -> set[str]:
    ids: set[str] = set()
    for index, record in enumerate(records):
        location = f"{prefix}[{index}].{field}"
        value = record.get(field)
        if text(value, location, findings):
            assert isinstance(value, str)
            if value in ids:
                add(findings, "error", "duplicate_id", location, f"duplicates {value!r}")
            ids.add(value)
    return ids


def confirmatory_fingerprint(data: dict[str, Any]) -> str:
    """Hash the complete design contract while excluding its self-referential lock."""

    frozen_payload = {
        key: value for key, value in data.items() if key != "confirmatory_lock"
    }
    canonical = json.dumps(
        frozen_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def design_fingerprint(data: dict[str, Any]) -> str:
    """Hash design state while excluding runtime pilots and the final freeze lock."""

    design_payload = {
        key: value
        for key, value in data.items()
        if key not in {"confirmatory_lock", "pilot_runs"}
    }
    canonical = json.dumps(
        design_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def unresolved(
    findings: list[Finding],
    code: str,
    location: str,
    message: str,
    *,
    strict_confirmatory: bool,
) -> None:
    """Represent a safe planning decision without letting it pass the strict gate."""

    add(
        findings,
        "error" if strict_confirmatory else "warning",
        code,
        location,
        message,
    )


def validate_confirmatory_lock(
    data: dict[str, Any],
    expected_fingerprint: str,
    findings: list[Finding],
    *,
    strict_confirmatory: bool,
) -> None:
    lock = data.get("confirmatory_lock")
    if not isinstance(lock, dict):
        add(
            findings,
            "error",
            "required_object",
            "confirmatory_lock",
            "must be an object",
        )
        return

    status = lock.get("status")
    if not isinstance(status, str) or status not in CONFIRMATORY_LOCK_STATES:
        add(
            findings,
            "error",
            "invalid_confirmatory_lock_state",
            "confirmatory_lock.status",
            f"expected one of {sorted(CONFIRMATORY_LOCK_STATES)}",
        )

    recorded_fingerprint = lock.get("contract_fingerprint")
    if recorded_fingerprint is not None:
        if not isinstance(recorded_fingerprint, str) or SHA256_RE.fullmatch(recorded_fingerprint) is None:
            add(
                findings,
                "error",
                "invalid_confirmatory_fingerprint",
                "confirmatory_lock.contract_fingerprint",
                "must be null or exactly 64 hexadecimal characters",
            )
        elif recorded_fingerprint.lower() != expected_fingerprint:
            add(
                findings,
                "error",
                "confirmatory_fingerprint_mismatch",
                "confirmatory_lock.contract_fingerprint",
                f"recorded {recorded_fingerprint.lower()}, expected {expected_fingerprint}",
            )

    frozen_before_final = lock.get("frozen_before_final_evaluation")
    if frozen_before_final is not None and not isinstance(frozen_before_final, bool):
        add(
            findings,
            "error",
            "required_boolean",
            "confirmatory_lock.frozen_before_final_evaluation",
            "must be true, false, or null while open",
        )

    evidence = lock.get("evidence")
    if evidence is not None:
        text(evidence, "confirmatory_lock.evidence", findings)

    freeze_required = strict_confirmatory or status == "frozen"
    if not freeze_required:
        return
    if status != "frozen":
        add(
            findings,
            "error",
            "confirmatory_lock_open",
            "confirmatory_lock.status",
            "--strict-confirmatory requires status 'frozen'",
        )
    if recorded_fingerprint is None:
        add(
            findings,
            "error",
            "missing_confirmatory_fingerprint",
            "confirmatory_lock.contract_fingerprint",
            "a frozen confirmatory contract requires its computed fingerprint",
        )
    if frozen_before_final is not True:
        add(
            findings,
            "error",
            "confirmatory_conditions_not_prelocked",
            "confirmatory_lock.frozen_before_final_evaluation",
            "must be true before final evaluation data are opened",
        )
    if evidence is None:
        add(
            findings,
            "error",
            "missing_confirmatory_lock_evidence",
            "confirmatory_lock.evidence",
            "a frozen confirmatory contract requires verification evidence",
        )


def validate(
    data: Any,
    *,
    strict_confirmatory: bool = False,
) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(data, dict):
        return [Finding("error", "root_type", "$", "root must be a JSON object")]
    expected_fingerprint = confirmatory_fingerprint(data)
    expected_design_fingerprint = design_fingerprint(data)
    if data.get("schema_version") != SCHEMA_VERSION:
        add(
            findings,
            "error",
            "schema_version",
            "schema_version",
            f"expected {SCHEMA_VERSION!r}",
        )
    for field in ("benchmark_id", "target_use", "optimization_object", "population_and_ploidy"):
        text(data.get(field), field, findings)

    truth = data.get("truth")
    if not isinstance(truth, dict):
        add(findings, "error", "required_object", "truth", "must be an object")
    else:
        for field in ("truth_id", "definition", "split_unit", "verification"):
            text(truth.get(field), f"truth.{field}", findings)
        string_list(truth.get("hidden_from"), "truth.hidden_from", findings)

    universe = data.get("evaluation_universe")
    if not isinstance(universe, dict):
        add(
            findings,
            "error",
            "required_object",
            "evaluation_universe",
            "must be an object",
        )
        universe = {}
    else:
        for field in ("authority", "requested_site_rule", "evaluable_rule", "missingness_rule"):
            text(universe.get(field), f"evaluation_universe.{field}", findings)
        for field in ("native_reported_set", "common_evaluation_set"):
            value = universe.get(field)
            if value is None:
                unresolved(
                    findings,
                    "unresolved_evaluation_universe",
                    f"evaluation_universe.{field}",
                    "may remain null during planning but must be true or false before confirmation",
                    strict_confirmatory=strict_confirmatory,
                )
            elif not isinstance(value, bool):
                add(
                    findings,
                    "error",
                    "required_boolean",
                    f"evaluation_universe.{field}",
                    "must be true or false",
                )

    conditions = object_list(data.get("conditions"), "conditions", findings)
    condition_ids = collect_ids(conditions, "condition_id", "conditions", findings)
    for index, condition in enumerate(conditions):
        dimensions = condition.get("dimensions")
        if not isinstance(dimensions, dict) or not dimensions:
            add(
                findings,
                "error",
                "required_object",
                f"conditions[{index}].dimensions",
                "must contain at least one stratification dimension",
            )
        elif any(
            not isinstance(key, str)
            or not key.strip()
            or value is None
            or isinstance(value, bool)
            or isinstance(value, (dict, list))
            or (isinstance(value, str) and not value.strip())
            for key, value in dimensions.items()
        ):
            add(
                findings,
                "error",
                "invalid_dimensions",
                f"conditions[{index}].dimensions",
                "keys and values must be non-empty scalar values",
            )

    inputs = object_list(data.get("input_registry"), "input_registry", findings)
    input_ids = collect_ids(inputs, "input_id", "input_registry", findings)
    input_by_id: dict[str, dict[str, Any]] = {}
    for index, input_record in enumerate(inputs):
        loc = f"input_registry[{index}]"
        input_id = input_record.get("input_id")
        if isinstance(input_id, str) and input_id in input_ids:
            input_by_id[input_id] = input_record
        role = input_record.get("role")
        if text(role, f"{loc}.role", findings):
            assert isinstance(role, str)
            if role not in INPUT_ROLES:
                add(
                    findings,
                    "error",
                    "invalid_input_role",
                    f"{loc}.role",
                    f"expected one of {sorted(INPUT_ROLES)}",
                )
        data_type = input_record.get("data_type")
        if text(data_type, f"{loc}.data_type", findings):
            assert isinstance(data_type, str)
            if data_type not in INPUT_TYPES:
                add(
                    findings,
                    "error",
                    "invalid_input_type",
                    f"{loc}.data_type",
                    f"expected one of {sorted(INPUT_TYPES)}",
                )
        status = input_record.get("status")
        if not isinstance(status, str) or status not in INPUT_STATES:
            add(
                findings,
                "error",
                "invalid_input_status",
                f"{loc}.status",
                f"expected one of {sorted(INPUT_STATES)}",
            )
        elif status == "open":
            add(
                findings,
                "warning",
                "open_input",
                f"{loc}.status",
                "input identity is not yet verified",
            )

        for field in ("authority", "version", "verification"):
            value = input_record.get(field)
            if status == "verified":
                text(value, f"{loc}.{field}", findings)
            elif value is not None:
                text(value, f"{loc}.{field}", findings)
        truth_flag = input_record.get("contains_evaluation_truth")
        if status == "verified" and not isinstance(truth_flag, bool):
            add(
                findings,
                "error",
                "unverified_truth_boundary",
                f"{loc}.contains_evaluation_truth",
                "a verified input must declare true or false",
            )
        elif truth_flag is not None and not isinstance(truth_flag, bool):
            add(
                findings,
                "error",
                "required_boolean",
                f"{loc}.contains_evaluation_truth",
                "must be true, false, or null while open",
            )
        if not isinstance(input_record.get("extensions"), dict):
            add(findings, "error", "required_object", f"{loc}.extensions", "must be an object")

    workflows = object_list(data.get("workflows"), "workflows", findings)
    workflow_ids = collect_ids(workflows, "workflow_id", "workflows", findings)
    workflow_by_id: dict[str, dict[str, Any]] = {}
    confirmatory_workflow_ids: set[str] = set()
    if len(workflows) == 1:
        add(
            findings,
            "warning",
            "single_workflow",
            "workflows",
            "one workflow can be audited, but a comparison normally needs another workflow, baseline, or ablation",
        )
    for index, workflow in enumerate(workflows):
        loc = f"workflows[{index}]"
        workflow_id = workflow.get("workflow_id")
        if isinstance(workflow_id, str) and workflow_id in workflow_ids:
            workflow_by_id[workflow_id] = workflow
        for field in ("version", "reference_context", "tuning_budget", "failure_rule"):
            text(workflow.get(field), f"{loc}.{field}", findings)
        comparison_role = workflow.get("comparison_role")
        if not isinstance(comparison_role, str) or comparison_role not in ROLES:
            add(
                findings,
                "error",
                "invalid_role",
                f"{loc}.comparison_role",
                f"expected one of {sorted(ROLES)}",
            )
        target_interface = workflow.get("target_interface")
        if not isinstance(target_interface, str) or target_interface not in INTERFACES:
            add(
                findings,
                "error",
                "invalid_interface",
                f"{loc}.target_interface",
                f"expected one of {sorted(INTERFACES)}",
            )
        confirmatory = workflow.get("confirmatory")
        if confirmatory is None:
            unresolved(
                findings,
                "unresolved_confirmatory_role",
                f"{loc}.confirmatory",
                "may remain null during planning but every workflow needs a role before confirmation",
                strict_confirmatory=strict_confirmatory,
            )
        elif not isinstance(confirmatory, bool):
            add(
                findings,
                "error",
                "required_boolean",
                f"{loc}.confirmatory",
                "must be true, false, or null while planning",
            )
        elif confirmatory and isinstance(workflow_id, str):
            confirmatory_workflow_ids.add(workflow_id)

        transductive = workflow.get("transductive")
        if transductive is None:
            unresolved(
                findings,
                "unresolved_transductive_status",
                f"{loc}.transductive",
                "may remain null during planning but must be resolved before confirmation",
                strict_confirmatory=strict_confirmatory,
            )
        elif not isinstance(transductive, bool):
            add(
                findings,
                "error",
                "required_boolean",
                f"{loc}.transductive",
                "must be true or false",
            )
        workflow_input_ids = string_list(workflow.get("input_ids"), f"{loc}.input_ids", findings)
        for input_id in workflow_input_ids:
            if input_id not in input_ids:
                add(
                    findings,
                    "error",
                    "unknown_input_id",
                    f"{loc}.input_ids",
                    repr(input_id),
                )
                continue
            input_record = input_by_id[input_id]
            status = input_record.get("status")
            truth_flag = input_record.get("contains_evaluation_truth")
            if status == "retired":
                add(
                    findings,
                    "error",
                    "retired_input_used",
                    f"{loc}.input_ids",
                    f"input {input_id!r} is retired",
                )
            if truth_flag is True:
                add(
                    findings,
                    "error",
                    "evaluation_truth_as_input",
                    f"{loc}.input_ids",
                    f"input {input_id!r} explicitly contains evaluation truth",
                )
            if status != "verified" or truth_flag is None:
                unresolved(
                    findings,
                    "unclosed_input_contract",
                    f"{loc}.input_ids",
                    f"input {input_id!r} must be verified and explicitly truth-free",
                    strict_confirmatory=strict_confirmatory and confirmatory is True,
                )

        output_fields = string_list(
            workflow.get("output_fields"),
            f"{loc}.output_fields",
            findings,
            nonempty=False,
        )
        if not output_fields:
            unresolved(
                findings,
                "unresolved_output_fields",
                f"{loc}.output_fields",
                "output fields may be empty during planning but must be fixed before confirmation",
                strict_confirmatory=strict_confirmatory and confirmatory is True,
            )
        if not isinstance(workflow.get("extensions"), dict):
            add(findings, "error", "required_object", f"{loc}.extensions", "must be an object")

    if strict_confirmatory and not confirmatory_workflow_ids:
        add(
            findings,
            "error",
            "missing_confirmatory_workflow",
            "workflows",
            "--strict-confirmatory requires at least one workflow with confirmatory=true",
        )

    metrics = object_list(data.get("metrics"), "metrics", findings)
    metric_ids = collect_ids(metrics, "metric_id", "metrics", findings)
    for index, metric in enumerate(metrics):
        loc = f"metrics[{index}]"
        for field in (
            "formula",
            "truth_representation",
            "imputed_representation",
            "unit",
            "aggregation",
            "missingness",
            "monomorphic_sites",
            "allele_frequency_source",
        ):
            text(metric.get(field), f"{loc}.{field}", findings)
        evaluation_set = metric.get("evaluation_set")
        if text(evaluation_set, f"{loc}.evaluation_set", findings):
            assert isinstance(evaluation_set, str)
            if evaluation_set not in METRIC_EVALUATION_SETS:
                add(
                    findings,
                    "error",
                    "invalid_metric_evaluation_set",
                    f"{loc}.evaluation_set",
                    f"expected one of {sorted(METRIC_EVALUATION_SETS)}",
                )
            else:
                required_sets = (
                    EVALUATION_SETS if evaluation_set == "both" else {evaluation_set}
                )
                for required_set in required_sets:
                    flag = (
                        "native_reported_set"
                        if required_set == "native"
                        else "common_evaluation_set"
                    )
                    if universe.get(flag) is not True:
                        add(
                            findings,
                            "error"
                            if strict_confirmatory or universe.get(flag) is False
                            else "warning",
                            "undefined_metric_evaluation_set",
                            f"{loc}.evaluation_set",
                            f"metric requires {required_set!r} but evaluation_universe.{flag} is not true",
                        )

    leakage = object_list(data.get("leakage_ledger"), "leakage_ledger", findings)
    collect_ids(leakage, "channel_id", "leakage_ledger", findings)
    for index, channel in enumerate(leakage):
        loc = f"leakage_ledger[{index}]"
        for field in ("channel", "control", "evidence"):
            text(channel.get(field), f"{loc}.{field}", findings)
        status = channel.get("status")
        if not isinstance(status, str) or status not in LEAKAGE_STATES:
            add(
                findings,
                "error",
                "invalid_leakage_status",
                f"{loc}.status",
                f"expected one of {sorted(LEAKAGE_STATES)}",
            )
        elif status == "open":
            add(
                findings,
                "error" if strict_confirmatory else "warning",
                "open_leakage_channel",
                f"{loc}.status",
                (
                    "open leakage channels block --strict-confirmatory"
                    if strict_confirmatory
                    else "must be controlled before confirmatory evaluation"
                ),
            )

    comparisons = object_list(data.get("required_comparisons"), "required_comparisons", findings)
    collect_ids(comparisons, "comparison_id", "required_comparisons", findings)
    covered_workflows: set[str] = set()
    covered_metrics: set[str] = set()
    covered_conditions: set[str] = set()
    comparison_pairs: set[tuple[str, str]] = set()
    for index, comparison in enumerate(comparisons):
        loc = f"required_comparisons[{index}]"
        references = {
            "workflow_ids": (workflow_ids, covered_workflows),
            "condition_ids": (condition_ids, covered_conditions),
            "metric_ids": (metric_ids, covered_metrics),
        }
        resolved_references: dict[str, list[str]] = {}
        for field, (known, covered) in references.items():
            values = string_list(comparison.get(field), f"{loc}.{field}", findings)
            resolved_references[field] = values
            for value in values:
                if value not in known:
                    add(findings, "error", "unknown_id", f"{loc}.{field}", repr(value))
                else:
                    covered.add(value)
        for workflow_id in resolved_references.get("workflow_ids", []):
            for condition_id in resolved_references.get("condition_ids", []):
                if workflow_id in workflow_ids and condition_id in condition_ids:
                    comparison_pairs.add((workflow_id, condition_id))
        sets = string_list(comparison.get("evaluation_sets"), f"{loc}.evaluation_sets", findings)
        for value in sets:
            if value not in EVALUATION_SETS:
                add(
                    findings,
                    "error",
                    "invalid_evaluation_set",
                    f"{loc}.evaluation_sets",
                    repr(value),
                )
            if value in EVALUATION_SETS:
                flag = (
                    "native_reported_set" if value == "native" else "common_evaluation_set"
                )
                if universe.get(flag) is not True:
                    add(
                        findings,
                        "error"
                        if strict_confirmatory or universe.get(flag) is False
                        else "warning",
                        "undefined_evaluation_set",
                        f"{loc}.evaluation_sets",
                        f"comparison requires {value!r} but evaluation_universe.{flag} is not true",
                    )

    for label, known, covered in (
        ("workflow", workflow_ids, covered_workflows),
        ("metric", metric_ids, covered_metrics),
        ("condition", condition_ids, covered_conditions),
    ):
        for missing in sorted(known - covered):
            add(
                findings,
                "error",
                "uncovered_contract_item",
                "required_comparisons",
                f"{label} {missing!r} is never evaluated",
            )

    pilots = object_list(data.get("pilot_runs"), "pilot_runs", findings, nonempty=False)
    collect_ids(pilots, "pilot_id", "pilot_runs", findings)
    current_passed_pilots: set[str] = set()
    for index, pilot in enumerate(pilots):
        loc = f"pilot_runs[{index}]"
        pilot_workflow_id = pilot.get("workflow_id")
        pilot_condition_id = pilot.get("condition_id")
        workflow_ok = text(pilot_workflow_id, f"{loc}.workflow_id", findings)
        condition_ok = text(pilot_condition_id, f"{loc}.condition_id", findings)
        if workflow_ok and pilot_workflow_id not in workflow_ids:
            add(findings, "error", "unknown_workflow_id", f"{loc}.workflow_id", repr(pilot_workflow_id))
            workflow_ok = False
        if condition_ok and pilot_condition_id not in condition_ids:
            add(findings, "error", "unknown_condition_id", f"{loc}.condition_id", repr(pilot_condition_id))
            condition_ok = False

        state = pilot.get("state")
        if not isinstance(state, str) or state not in PILOT_STATES:
            add(
                findings,
                "error",
                "invalid_pilot_state",
                f"{loc}.state",
                f"expected one of {sorted(PILOT_STATES)}",
            )

        recorded_design = pilot.get("design_fingerprint")
        design_syntax_ok = recorded_design is None
        if recorded_design is not None:
            if not isinstance(recorded_design, str) or SHA256_RE.fullmatch(recorded_design) is None:
                add(
                    findings,
                    "error",
                    "invalid_design_fingerprint",
                    f"{loc}.design_fingerprint",
                    "must be null or exactly 64 hexadecimal characters",
                )
            else:
                design_syntax_ok = True

        output_validation = pilot.get("output_validation")
        validation_status: Any = None
        verified_fields: list[str] = []
        evidence: Any = None
        if not isinstance(output_validation, dict):
            add(
                findings,
                "error",
                "required_object",
                f"{loc}.output_validation",
                "must be an object",
            )
        else:
            validation_status = output_validation.get("status")
            if not isinstance(validation_status, str) or validation_status not in PILOT_VALIDATION_STATES:
                add(
                    findings,
                    "error",
                    "invalid_pilot_validation_state",
                    f"{loc}.output_validation.status",
                    f"expected one of {sorted(PILOT_VALIDATION_STATES)}",
                )
            verified_fields = string_list(
                output_validation.get("verified_fields"),
                f"{loc}.output_validation.verified_fields",
                findings,
                nonempty=False,
            )
            evidence = output_validation.get("evidence")
            if evidence is not None:
                text(evidence, f"{loc}.output_validation.evidence", findings)

        passed_and_current = state == "passed"
        if state == "passed":
            if recorded_design is None:
                add(
                    findings,
                    "error",
                    "missing_design_fingerprint",
                    f"{loc}.design_fingerprint",
                    "a passed pilot must bind the current design fingerprint",
                )
                passed_and_current = False
            elif design_syntax_ok and str(recorded_design).lower() != expected_design_fingerprint:
                add(
                    findings,
                    "error",
                    "stale_pilot_design",
                    f"{loc}.design_fingerprint",
                    f"recorded {str(recorded_design).lower()}, expected {expected_design_fingerprint}",
                )
                passed_and_current = False
            if validation_status != "passed":
                add(
                    findings,
                    "error",
                    "pilot_output_not_validated",
                    f"{loc}.output_validation.status",
                    "a passed pilot requires passed output validation",
                )
                passed_and_current = False
            if evidence is None:
                add(
                    findings,
                    "error",
                    "missing_pilot_evidence",
                    f"{loc}.output_validation.evidence",
                    "a passed pilot requires output-validation evidence",
                )
                passed_and_current = False
            if workflow_ok and isinstance(pilot_workflow_id, str):
                required_output_fields = set(
                    item
                    for item in workflow_by_id[pilot_workflow_id].get("output_fields", [])
                    if isinstance(item, str)
                )
                missing_fields = required_output_fields - set(verified_fields)
                if missing_fields:
                    add(
                        findings,
                        "error",
                        "pilot_output_fields_unverified",
                        f"{loc}.output_validation.verified_fields",
                        f"missing {sorted(missing_fields)!r}",
                    )
                    passed_and_current = False
            if (
                workflow_ok
                and condition_ok
                and isinstance(pilot_workflow_id, str)
                and isinstance(pilot_condition_id, str)
                and (pilot_workflow_id, pilot_condition_id) not in comparison_pairs
            ):
                add(
                    findings,
                    "error",
                    "pilot_outside_comparison",
                    loc,
                    "passed pilot workflow and condition are not paired in required_comparisons",
                )
                passed_and_current = False
        elif validation_status == "passed":
            add(
                findings,
                "error",
                "pilot_state_validation_mismatch",
                f"{loc}.output_validation.status",
                "passed output validation requires pilot state 'passed'",
            )

        if passed_and_current and workflow_ok and condition_ok and isinstance(pilot_workflow_id, str):
            current_passed_pilots.add(pilot_workflow_id)
        if not isinstance(pilot.get("extensions"), dict):
            add(findings, "error", "required_object", f"{loc}.extensions", "must be an object")

    if strict_confirmatory:
        for workflow_id in sorted(confirmatory_workflow_ids - current_passed_pilots):
            add(
                findings,
                "error",
                "missing_current_pilot",
                "pilot_runs",
                f"confirmatory workflow {workflow_id!r} lacks a passed pilot bound to the current design",
            )

    downstream = data.get("downstream_validation")
    downstream_applicability: Any = None
    endpoints: list[dict[str, Any]] = []
    confirmatory_endpoint_coverage: set[str] = set()
    if not isinstance(downstream, dict):
        add(
            findings,
            "error",
            "required_object",
            "downstream_validation",
            "must be an object",
        )
    else:
        downstream_applicability = downstream.get("applicability")
        if not isinstance(downstream_applicability, str) or downstream_applicability not in DOWNSTREAM_APPLICABILITY:
            add(
                findings,
                "error",
                "invalid_downstream_applicability",
                "downstream_validation.applicability",
                f"expected one of {sorted(DOWNSTREAM_APPLICABILITY)}",
            )
        elif downstream_applicability == "open":
            unresolved(
                findings,
                "unresolved_downstream_applicability",
                "downstream_validation.applicability",
                "may remain open during planning but must be resolved before confirmation",
                strict_confirmatory=strict_confirmatory,
            )

        reason = downstream.get("reason")
        if reason is not None:
            text(reason, "downstream_validation.reason", findings)
        endpoints = object_list(
            downstream.get("endpoints"),
            "downstream_validation.endpoints",
            findings,
            nonempty=False,
        )
        if downstream_applicability == "not-applicable":
            if reason is None:
                add(
                    findings,
                    "error",
                    "missing_downstream_reason",
                    "downstream_validation.reason",
                    "not-applicable requires a reason",
                )
            if endpoints:
                add(
                    findings,
                    "error",
                    "endpoints_when_not_applicable",
                    "downstream_validation.endpoints",
                    "must be empty when downstream validation is not applicable",
                )
            if data.get("target_use") == "downstream-analysis":
                add(
                    findings,
                    "error",
                    "downstream_target_without_validation",
                    "downstream_validation.applicability",
                    "target_use 'downstream-analysis' cannot be not-applicable",
                )
        elif downstream_applicability == "required" and not endpoints:
            unresolved(
                findings,
                "missing_downstream_endpoint",
                "downstream_validation.endpoints",
                "required downstream validation needs at least one endpoint",
                strict_confirmatory=strict_confirmatory,
            )

        collect_ids(endpoints, "endpoint_id", "downstream_validation.endpoints", findings)
        for index, endpoint in enumerate(endpoints):
            loc = f"downstream_validation.endpoints[{index}]"
            text(endpoint.get("task"), f"{loc}.task", findings)
            role = endpoint.get("role")
            if role is None:
                unresolved(
                    findings,
                    "unresolved_downstream_role",
                    f"{loc}.role",
                    "may remain null during planning but must be resolved before confirmation",
                    strict_confirmatory=strict_confirmatory,
                )
            elif not isinstance(role, str) or role not in DOWNSTREAM_ROLES:
                add(
                    findings,
                    "error",
                    "invalid_downstream_role",
                    f"{loc}.role",
                    f"expected one of {sorted(DOWNSTREAM_ROLES)} or null",
                )

            endpoint_workflows = string_list(endpoint.get("workflow_ids"), f"{loc}.workflow_ids", findings)
            endpoint_conditions = string_list(endpoint.get("condition_ids"), f"{loc}.condition_ids", findings)
            endpoint_fields = string_list(endpoint.get("input_fields"), f"{loc}.input_fields", findings)
            known_endpoint_workflows: list[str] = []
            for workflow_id in endpoint_workflows:
                if workflow_id not in workflow_ids:
                    add(findings, "error", "unknown_workflow_id", f"{loc}.workflow_ids", repr(workflow_id))
                else:
                    known_endpoint_workflows.append(workflow_id)
            for condition_id in endpoint_conditions:
                if condition_id not in condition_ids:
                    add(findings, "error", "unknown_condition_id", f"{loc}.condition_ids", repr(condition_id))
            for workflow_id in known_endpoint_workflows:
                available = {
                    item
                    for item in workflow_by_id[workflow_id].get("output_fields", [])
                    if isinstance(item, str)
                }
                missing_fields = set(endpoint_fields) - available
                if missing_fields:
                    add(
                        findings,
                        "error",
                        "unknown_downstream_input_field",
                        f"{loc}.input_fields",
                        f"workflow {workflow_id!r} does not emit {sorted(missing_fields)!r}",
                    )

            analysis_plan = endpoint.get("analysis_plan")
            if analysis_plan is None:
                unresolved(
                    findings,
                    "missing_downstream_analysis_plan",
                    f"{loc}.analysis_plan",
                    "may remain null during planning but is required for confirmation",
                    strict_confirmatory=strict_confirmatory and role == "confirmatory",
                )
            else:
                text(analysis_plan, f"{loc}.analysis_plan", findings)

            outcomes = object_list(endpoint.get("outcomes"), f"{loc}.outcomes", findings, nonempty=False)
            collect_ids(outcomes, "outcome_id", f"{loc}.outcomes", findings)
            if not outcomes:
                unresolved(
                    findings,
                    "missing_downstream_outcome",
                    f"{loc}.outcomes",
                    "may remain empty during planning but is required for confirmation",
                    strict_confirmatory=strict_confirmatory and role == "confirmatory",
                )
            for outcome_index, outcome in enumerate(outcomes):
                outcome_loc = f"{loc}.outcomes[{outcome_index}]"
                for field in ("definition", "unit", "analysis_rule"):
                    text(outcome.get(field), f"{outcome_loc}.{field}", findings)
                acceptance_rule = outcome.get("acceptance_rule")
                if acceptance_rule is None:
                    unresolved(
                        findings,
                        "missing_downstream_acceptance_rule",
                        f"{outcome_loc}.acceptance_rule",
                        "may remain null during planning but is required for confirmation",
                        strict_confirmatory=strict_confirmatory and role == "confirmatory",
                    )
                else:
                    text(acceptance_rule, f"{outcome_loc}.acceptance_rule", findings)

            endpoint_status = endpoint.get("status")
            if not isinstance(endpoint_status, str) or endpoint_status not in DOWNSTREAM_STATES:
                add(
                    findings,
                    "error",
                    "invalid_downstream_status",
                    f"{loc}.status",
                    f"expected one of {sorted(DOWNSTREAM_STATES)}",
                )
            elif endpoint_status == "open":
                unresolved(
                    findings,
                    "open_downstream_endpoint",
                    f"{loc}.status",
                    "may remain open during planning but a confirmatory endpoint must be ready or completed",
                    strict_confirmatory=strict_confirmatory and role == "confirmatory",
                )
            elif strict_confirmatory and role == "confirmatory" and endpoint_status not in {"ready", "completed"}:
                add(
                    findings,
                    "error",
                    "downstream_endpoint_not_ready",
                    f"{loc}.status",
                    "a confirmatory endpoint must be ready or completed",
                )

            verification = endpoint.get("verification")
            if verification is None:
                unresolved(
                    findings,
                    "missing_downstream_verification",
                    f"{loc}.verification",
                    "may remain null during planning but is required for confirmation",
                    strict_confirmatory=strict_confirmatory and role == "confirmatory",
                )
            else:
                text(verification, f"{loc}.verification", findings)

            if role == "confirmatory":
                confirmatory_endpoint_coverage.update(
                    workflow_id
                    for workflow_id in known_endpoint_workflows
                    if workflow_id in confirmatory_workflow_ids
                )
            if not isinstance(endpoint.get("extensions"), dict):
                add(findings, "error", "required_object", f"{loc}.extensions", "must be an object")

        if not isinstance(downstream.get("extensions"), dict):
            add(
                findings,
                "error",
                "required_object",
                "downstream_validation.extensions",
                "must be an object",
            )

    if strict_confirmatory and downstream_applicability == "required":
        for workflow_id in sorted(confirmatory_workflow_ids - confirmatory_endpoint_coverage):
            add(
                findings,
                "error",
                "confirmatory_workflow_without_downstream_endpoint",
                "downstream_validation.endpoints",
                f"confirmatory workflow {workflow_id!r} lacks confirmatory endpoint coverage",
            )

    string_list(data.get("compute_reporting"), "compute_reporting", findings)
    if not isinstance(data.get("extensions"), dict):
        add(findings, "error", "required_object", "extensions", "must be an object")
    validate_confirmatory_lock(
        data,
        expected_fingerprint,
        findings,
        strict_confirmatory=strict_confirmatory,
    )
    return sorted(findings, key=lambda item: (item.severity, item.code, item.location, item.message))


def emit(
    findings: list[Finding],
    output_format: str,
    contract: Path,
    *,
    strict_confirmatory: bool,
    confirmatory_fingerprint_value: str | None,
    design_fingerprint_value: str | None,
) -> None:
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    if output_format == "json":
        print(
            json.dumps(
                {
                    "contract": contract.as_posix(),
                    "errors": errors,
                    "warnings": warnings,
                    "strict_confirmatory": strict_confirmatory,
                    "design_fingerprint": design_fingerprint_value,
                    "confirmatory_fingerprint": confirmatory_fingerprint_value,
                    "findings": [asdict(item) for item in findings],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return
    if design_fingerprint_value is not None:
        print(f"DESIGN_FINGERPRINT: {design_fingerprint_value}")
    if confirmatory_fingerprint_value is not None:
        print(f"CONFIRMATORY_FINGERPRINT: {confirmatory_fingerprint_value}")
    for item in findings:
        print(f"{item.severity.upper()} {item.code} {item.location}: {item.message}")
    print(f"RESULT: {'FAIL' if errors else 'PASS'} ({errors} error(s), {warnings} warning(s))")


def main() -> int:
    configure_standard_streams()
    args = parse_args()
    try:
        data = load_strict_json(args.contract)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: cannot read benchmark contract: {exc}", file=sys.stderr)
        return 2
    confirmatory_fingerprint_value = (
        confirmatory_fingerprint(data) if isinstance(data, dict) else None
    )
    design_fingerprint_value = design_fingerprint(data) if isinstance(data, dict) else None
    findings = validate(data, strict_confirmatory=args.strict_confirmatory)
    emit(
        findings,
        args.output_format,
        args.contract,
        strict_confirmatory=args.strict_confirmatory,
        confirmatory_fingerprint_value=confirmatory_fingerprint_value,
        design_fingerprint_value=design_fingerprint_value,
    )
    return 1 if any(item.severity == "error" for item in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
