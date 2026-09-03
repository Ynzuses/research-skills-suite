#!/usr/bin/env python3
"""Validate a species-aware genomics study contract without judging biology."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
STUDY_MODES = {
    "association-only",
    "existing-genotypes",
    "reference-audit",
    "variant-discovery",
}
APPLICABILITY_STATES = {"applicable", "not-applicable"}
MAPPING_FIELDS = (
    "aligner_and_version",
    "caller_and_version",
    "ploidy_assumption",
    "callable_space",
    "interval_strategy",
    "stepwise_count_record",
)
QC_LEVELS = {"reference", "read", "site", "genotype", "sample", "population"}
HYPOTHESIS_STATES = {"provisional", "approved", "rejected", "superseded"}
NON_CONCRETE_REASONS = {
    "n/a",
    "na",
    "no",
    "no mapping",
    "no split",
    "none",
    "not applicable",
    "not needed",
    "not required",
    "tbd",
    "todo",
    "unknown",
    "unresolved",
    "不适用",
    "无",
    "暂无",
    "待定",
    "未知",
}


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
        description="Validate a genomics study-contract JSON without modifying it."
    )
    parser.add_argument("contract", type=Path)
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


def concrete_reason(value: Any, location: str, findings: list[Finding]) -> bool:
    if not required_text(value, location, findings):
        return False
    assert isinstance(value, str)
    normalized = re.sub(r"[\s_-]+", " ", value.casefold()).strip(" .,:;")
    if normalized in NON_CONCRETE_REASONS:
        add(
            findings,
            "non_concrete_reason",
            location,
            "must explain why the module is not applicable; a sentinel is insufficient",
        )
        return False
    return True


def required_list(
    value: Any, location: str, findings: list[Finding], *, allow_empty: bool = False
) -> list[Any]:
    if not isinstance(value, list) or (not allow_empty and not value):
        add(
            findings,
            "required_list",
            location,
            "must be a list" if allow_empty else "must be a non-empty list",
        )
        return []
    return value


def text_list(
    value: Any, location: str, findings: list[Finding], *, allow_empty: bool = False
) -> list[str]:
    result: list[str] = []
    items = required_list(value, location, findings, allow_empty=allow_empty)
    for index, item in enumerate(items):
        if required_text(item, f"{location}[{index}]", findings):
            assert isinstance(item, str)
            result.append(item)
    if len(set(result)) != len(result):
        add(findings, "duplicate_value", location, "contains duplicates")
    return result


def unique_id(
    value: Any, location: str, seen: set[str], findings: list[Finding]
) -> str | None:
    if not required_text(value, location, findings):
        return None
    assert isinstance(value, str)
    if value in seen:
        add(findings, "duplicate_id", location, f"duplicates {value!r}")
    else:
        seen.add(value)
    return value


def validate_extensions(
    record: dict[str, Any], location: str, findings: list[Finding], *, required: bool = False
) -> None:
    if "extensions" not in record and not required:
        return
    if not isinstance(record.get("extensions"), dict):
        add(findings, "required_object", f"{location}.extensions", "must be an object")


def validate_selection_and_tuning(
    data: dict[str, Any], findings: list[Finding]
) -> tuple[bool | None, list[str]]:
    selection = data.get("selection_and_tuning")
    if not isinstance(selection, dict):
        add(findings, "required_object", "selection_and_tuning", "must be an object")
        return None, []

    required = selection.get("required")
    if not isinstance(required, bool):
        add(
            findings,
            "required_boolean",
            "selection_and_tuning.required",
            "must be true or false",
        )
        required = None

    activities = text_list(
        selection.get("activities"),
        "selection_and_tuning.activities",
        findings,
        allow_empty=required is not True,
    )
    if required is False and activities:
        add(
            findings,
            "unexpected_selection_activity",
            "selection_and_tuning.activities",
            "must be empty when selection_and_tuning.required is false",
        )
    concrete_reason(selection.get("rationale"), "selection_and_tuning.rationale", findings)
    validate_extensions(selection, "selection_and_tuning", findings, required=True)
    return required, activities


def validate_split(
    data: dict[str, Any],
    selection_required: bool | None,
    selection_activities: list[str],
    findings: list[Finding],
) -> str | None:
    split = data.get("split")
    if not isinstance(split, dict):
        add(findings, "required_object", "split", "must be an object")
        if selection_required is True:
            add(
                findings,
                "split_required_for_selection",
                "split",
                "data-dependent selection or tuning requires an applicable split",
            )
        return None

    validate_extensions(split, "split", findings, required=True)
    applicability = split.get("applicability")
    if not isinstance(applicability, str) or applicability not in APPLICABILITY_STATES:
        add(
            findings,
            "invalid_applicability",
            "split.applicability",
            f"expected one of {sorted(APPLICABILITY_STATES)}",
        )
        applicability = None

    protected_from: list[str] = []
    if applicability == "applicable":
        if split.get("reason") is not None:
            add(
                findings,
                "unexpected_applicability_reason",
                "split.reason",
                "must be null when split is applicable",
            )
        required_text(split.get("split_unit"), "split.split_unit", findings)
        development = text_list(
            split.get("development_groups"), "split.development_groups", findings
        )
        held_out = text_list(split.get("held_out_groups"), "split.held_out_groups", findings)
        overlap = sorted(set(development) & set(held_out))
        if overlap:
            add(
                findings,
                "split_overlap",
                "split",
                f"groups occur in both development and held-out sets: {overlap}",
            )
        protected_from = text_list(
            split.get("protected_from"), "split.protected_from", findings
        )
        required_text(split.get("verification"), "split.verification", findings)
    elif applicability == "not-applicable":
        concrete_reason(split.get("reason"), "split.reason", findings)
        for field in ("split_unit", "verification"):
            if split.get(field) is not None:
                add(
                    findings,
                    "inapplicable_field_present",
                    f"split.{field}",
                    "must be null or omitted when split is not applicable",
                )
        for field in ("development_groups", "held_out_groups", "protected_from"):
            value = split.get(field)
            if value is not None and value != []:
                add(
                    findings,
                    "inapplicable_field_present",
                    f"split.{field}",
                    "must be empty or omitted when split is not applicable",
                )

    if selection_required is True:
        if applicability != "applicable":
            add(
                findings,
                "split_required_for_selection",
                "split.applicability",
                "data-dependent selection or tuning requires an applicable split",
            )
        else:
            for activity in selection_activities:
                if activity not in protected_from:
                    add(
                        findings,
                        "unprotected_selection_activity",
                        "split.protected_from",
                        f"does not protect held-out groups from {activity!r}",
                    )
    return applicability


def validate_mapping(
    data: dict[str, Any], study_mode: str | None, findings: list[Finding]
) -> str | None:
    mapping = data.get("mapping_and_variants")
    if not isinstance(mapping, dict):
        add(findings, "required_object", "mapping_and_variants", "must be an object")
        if study_mode == "variant-discovery":
            add(
                findings,
                "mapping_required_for_mode",
                "mapping_and_variants",
                "variant-discovery requires an applicable mapping and calling contract",
            )
        return None

    validate_extensions(mapping, "mapping_and_variants", findings, required=True)
    applicability = mapping.get("applicability")
    if not isinstance(applicability, str) or applicability not in APPLICABILITY_STATES:
        add(
            findings,
            "invalid_applicability",
            "mapping_and_variants.applicability",
            f"expected one of {sorted(APPLICABILITY_STATES)}",
        )
        applicability = None

    if applicability == "applicable":
        if mapping.get("reason") is not None:
            add(
                findings,
                "unexpected_applicability_reason",
                "mapping_and_variants.reason",
                "must be null when mapping and calling are applicable",
            )
        for field in MAPPING_FIELDS:
            required_text(mapping.get(field), f"mapping_and_variants.{field}", findings)
    elif applicability == "not-applicable":
        concrete_reason(mapping.get("reason"), "mapping_and_variants.reason", findings)
        for field in MAPPING_FIELDS:
            if mapping.get(field) is not None:
                add(
                    findings,
                    "inapplicable_field_present",
                    f"mapping_and_variants.{field}",
                    "must be null or omitted when mapping and calling are not applicable",
                )

    if study_mode == "variant-discovery" and applicability != "applicable":
        add(
            findings,
            "mapping_required_for_mode",
            "mapping_and_variants.applicability",
            "variant-discovery requires an applicable mapping and calling contract",
        )
    return applicability


def validate(data: Any) -> list[Finding]:
    findings: list[Finding] = []
    if not isinstance(data, dict):
        return [Finding("error", "root_type", "$", "root must be a JSON object")]

    if data.get("schema_version") != "1.1":
        add(findings, "schema_version", "schema_version", "expected '1.1'")

    study_mode = data.get("study_mode")
    if not isinstance(study_mode, str) or study_mode not in STUDY_MODES:
        add(
            findings,
            "invalid_study_mode",
            "study_mode",
            f"expected one of {sorted(STUDY_MODES)}",
        )
        study_mode = None

    for field in ("study_id", "biological_question", "estimand"):
        required_text(data.get(field), field, findings)

    organism = data.get("organism")
    if not isinstance(organism, dict):
        add(findings, "required_object", "organism", "must be an object")
    else:
        for field in ("name", "ploidy", "genome_history"):
            required_text(organism.get(field), f"organism.{field}", findings)
        validate_extensions(organism, "organism", findings)

    references = required_list(data.get("references"), "references", findings)
    reference_ids: set[str] = set()
    for index, reference in enumerate(references):
        loc = f"references[{index}]"
        if not isinstance(reference, dict):
            add(findings, "invalid_reference", loc, "must be an object")
            continue
        unique_id(reference.get("reference_id"), f"{loc}.reference_id", reference_ids, findings)
        for field in (
            "assembly_accession",
            "assembly_version",
            "annotation_release",
            "coordinate_system",
            "contig_naming",
            "verification",
        ):
            required_text(reference.get(field), f"{loc}.{field}", findings)
        validate_extensions(reference, loc, findings)

    samples = data.get("samples")
    if not isinstance(samples, dict):
        add(findings, "required_object", "samples", "must be an object")
    else:
        for field in (
            "stable_key",
            "inclusion_rule",
            "metadata_authority",
            "relatedness_and_groups",
            "truth_roles",
        ):
            required_text(samples.get(field), f"samples.{field}", findings)
        validate_extensions(samples, "samples", findings)

    selection_required, selection_activities = validate_selection_and_tuning(data, findings)
    validate_split(data, selection_required, selection_activities, findings)

    scales = set(text_list(data.get("analysis_scales"), "analysis_scales", findings))
    validate_mapping(data, study_mode, findings)

    qc_rules = required_list(data.get("qc_rules"), "qc_rules", findings)
    qc_ids: set[str] = set()
    for index, rule in enumerate(qc_rules):
        loc = f"qc_rules[{index}]"
        if not isinstance(rule, dict):
            add(findings, "invalid_qc_rule", loc, "must be an object")
            continue
        unique_id(rule.get("qc_id"), f"{loc}.qc_id", qc_ids, findings)
        level = rule.get("level")
        if not isinstance(level, str) or level not in QC_LEVELS:
            add(
                findings,
                "invalid_qc_level",
                f"{loc}.level",
                f"expected one of {sorted(QC_LEVELS)}",
            )
        for field in ("metric", "rule", "rationale", "distribution_evidence"):
            required_text(rule.get(field), f"{loc}.{field}", findings)
        destructive = rule.get("destructive")
        if not isinstance(destructive, bool):
            add(findings, "required_boolean", f"{loc}.destructive", "must be true or false")
        count_record = rule.get("stepwise_count_record")
        if destructive is True:
            required_text(count_record, f"{loc}.stepwise_count_record", findings)
        elif count_record is not None:
            required_text(count_record, f"{loc}.stepwise_count_record", findings)
        validate_extensions(rule, loc, findings)

    hypotheses = required_list(data.get("hypotheses"), "hypotheses", findings)
    hypothesis_ids: set[str] = set()
    hypothesis_evidence_refs: list[tuple[str, list[str]]] = []
    for index, hypothesis in enumerate(hypotheses):
        loc = f"hypotheses[{index}]"
        if not isinstance(hypothesis, dict):
            add(findings, "invalid_hypothesis", loc, "must be an object")
            continue
        unique_id(
            hypothesis.get("hypothesis_id"), f"{loc}.hypothesis_id", hypothesis_ids, findings
        )
        required_text(hypothesis.get("mechanism"), f"{loc}.mechanism", findings)
        scale = hypothesis.get("analysis_scale")
        if required_text(scale, f"{loc}.analysis_scale", findings) and scale not in scales:
            add(
                findings,
                "undeclared_scale",
                f"{loc}.analysis_scale",
                f"{scale!r} is not listed in analysis_scales",
            )
        required_text(hypothesis.get("proxy_or_annotation"), f"{loc}.proxy_or_annotation", findings)
        text_list(hypothesis.get("competing_explanations"), f"{loc}.competing_explanations", findings)
        evidence_refs = text_list(
            hypothesis.get("required_evidence_ids"),
            f"{loc}.required_evidence_ids",
            findings,
        )
        hypothesis_evidence_refs.append((f"{loc}.required_evidence_ids", evidence_refs))
        status = hypothesis.get("status")
        if not isinstance(status, str) or status not in HYPOTHESIS_STATES:
            add(
                findings,
                "invalid_hypothesis_state",
                f"{loc}.status",
                f"expected one of {sorted(HYPOTHESIS_STATES)}",
            )
        validate_extensions(hypothesis, loc, findings)

    evidence_requirements = required_list(
        data.get("evidence_requirements"), "evidence_requirements", findings
    )
    evidence_ids: set[str] = set()
    evidence_locations: dict[str, str] = {}
    evidence_links: dict[str, tuple[str, list[str], list[str]]] = {}
    for index, evidence in enumerate(evidence_requirements):
        loc = f"evidence_requirements[{index}]"
        if not isinstance(evidence, dict):
            add(findings, "invalid_evidence_requirement", loc, "must be an object")
            continue
        evidence_id = unique_id(
            evidence.get("evidence_id"), f"{loc}.evidence_id", evidence_ids, findings
        )
        required_text(evidence.get("description"), f"{loc}.description", findings)
        output_refs = text_list(evidence.get("output_ids"), f"{loc}.output_ids", findings)
        validation_refs = text_list(
            evidence.get("validation_ids"), f"{loc}.validation_ids", findings
        )
        if evidence_id is not None and evidence_id not in evidence_links:
            evidence_locations[evidence_id] = loc
            evidence_links[evidence_id] = (loc, output_refs, validation_refs)
        validate_extensions(evidence, loc, findings)

    expected_outputs = required_list(data.get("expected_outputs"), "expected_outputs", findings)
    output_ids: set[str] = set()
    output_locations: dict[str, str] = {}
    for index, output in enumerate(expected_outputs):
        loc = f"expected_outputs[{index}]"
        if not isinstance(output, dict):
            add(findings, "invalid_output", loc, "must be an object")
            continue
        output_id = unique_id(output.get("output_id"), f"{loc}.output_id", output_ids, findings)
        for field in ("description", "acceptance_criterion"):
            required_text(output.get(field), f"{loc}.{field}", findings)
        if output_id is not None and output_id not in output_locations:
            output_locations[output_id] = loc
        validate_extensions(output, loc, findings)

    validations = required_list(data.get("validations"), "validations", findings)
    validation_ids: set[str] = set()
    validation_locations: dict[str, str] = {}
    validation_outputs: dict[str, tuple[str, list[str]]] = {}
    for index, validation in enumerate(validations):
        loc = f"validations[{index}]"
        if not isinstance(validation, dict):
            add(findings, "invalid_validation", loc, "must be an object")
            continue
        validation_id = unique_id(
            validation.get("validation_id"),
            f"{loc}.validation_id",
            validation_ids,
            findings,
        )
        required_text(validation.get("method"), f"{loc}.method", findings)
        validation_output_refs = text_list(
            validation.get("output_ids"), f"{loc}.output_ids", findings
        )
        required_text(
            validation.get("acceptance_criterion"),
            f"{loc}.acceptance_criterion",
            findings,
        )
        if validation_id is not None and validation_id not in validation_outputs:
            validation_locations[validation_id] = loc
            validation_outputs[validation_id] = (loc, validation_output_refs)
        validate_extensions(validation, loc, findings)

    referenced_evidence: set[str] = set()
    for location, refs in hypothesis_evidence_refs:
        for ref in refs:
            if ref not in evidence_ids:
                add(findings, "unknown_evidence", location, repr(ref))
            else:
                referenced_evidence.add(ref)

    referenced_outputs: set[str] = set()
    referenced_validations: set[str] = set()
    for evidence_id, (loc, output_refs, validation_refs) in evidence_links.items():
        known_evidence_outputs: set[str] = set()
        for ref in output_refs:
            if ref not in output_ids:
                add(findings, "unknown_output", f"{loc}.output_ids", repr(ref))
            else:
                referenced_outputs.add(ref)
                known_evidence_outputs.add(ref)
        for ref in validation_refs:
            if ref not in validation_ids:
                add(findings, "unknown_validation", f"{loc}.validation_ids", repr(ref))
                continue
            referenced_validations.add(ref)
            linked_outputs = set(validation_outputs.get(ref, ("", []))[1]) & output_ids
            if known_evidence_outputs and not (known_evidence_outputs & linked_outputs):
                add(
                    findings,
                    "validation_output_mismatch",
                    f"{loc}.validation_ids",
                    f"{ref!r} validates none of evidence {evidence_id!r}'s outputs",
                )

    for validation_id, (loc, refs) in validation_outputs.items():
        for ref in refs:
            if ref not in output_ids:
                add(findings, "unknown_output", f"{loc}.output_ids", repr(ref))

    for evidence_id in sorted(evidence_ids - referenced_evidence):
        add(
            findings,
            "orphan_evidence",
            evidence_locations.get(evidence_id, "evidence_requirements"),
            f"{evidence_id!r} is not required by any hypothesis",
        )
    for output_id in sorted(output_ids - referenced_outputs):
        add(
            findings,
            "orphan_output",
            output_locations.get(output_id, "expected_outputs"),
            f"{output_id!r} is not required by any evidence record",
        )
    for validation_id in sorted(validation_ids - referenced_validations):
        add(
            findings,
            "orphan_validation",
            validation_locations.get(validation_id, "validations"),
            f"{validation_id!r} is not required by any evidence record",
        )

    linked_validated_outputs: set[str] = set()
    for validation_id in referenced_validations:
        linked_validated_outputs.update(validation_outputs.get(validation_id, ("", []))[1])
    for output_id in sorted(referenced_outputs - linked_validated_outputs):
        add(
            findings,
            "output_without_validation",
            output_locations.get(output_id, "expected_outputs"),
            f"{output_id!r} has no evidence-linked validation",
        )

    required_text(data.get("privacy_and_publication"), "privacy_and_publication", findings)
    if not isinstance(data.get("extensions"), dict):
        add(findings, "required_object", "extensions", "must be an object")
    return sorted(findings, key=lambda item: (item.code, item.location, item.message))


def emit(findings: list[Finding], output_format: str, contract: Path) -> None:
    if output_format == "json":
        print(
            json.dumps(
                {
                    "contract": contract.as_posix(),
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
    print(f"RESULT: {'FAIL' if findings else 'PASS'} ({len(findings)} error(s))")


def main() -> int:
    configure_standard_streams()
    args = parse_args()
    try:
        data = load_strict_json(args.contract)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: cannot read study contract: {exc}", file=sys.stderr)
        return 2
    findings = validate(data)
    emit(findings, args.output_format, args.contract)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
