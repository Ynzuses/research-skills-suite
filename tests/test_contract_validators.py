"""Synthetic regression tests for suite-owned JSON contract validators."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SUITE_ROOT = Path(__file__).resolve().parents[1]
VALIDATORS = (
    ("rigorous-research-workflow", "validate_workflow_state.py"),
    ("scientific-writing-and-revision", "validate_revision_state.py"),
    ("research-document-delivery", "verify_delivery_record.py"),
    ("reproducible-computational-research", "validate_run_manifest.py"),
    ("genomics-study-design", "validate_study_contract.py"),
    ("genotype-imputation-benchmarking", "validate_benchmark_contract.py"),
)


@contextmanager
def fixture_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f".contract-{uuid.uuid4().hex}"
    root.mkdir(parents=False, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root)


def run_validator(
    root: Path,
    skill: str,
    script: str,
    data: dict[str, Any],
    *,
    output_format: str = "json",
    extra_args: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    state = root / "record.json"
    state.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8", errors="strict")
    executable = SUITE_ROOT / skill / "scripts" / script
    return subprocess.run(
        [
            sys.executable,
            str(executable),
            str(state),
            "--format",
            output_format,
            *extra_args,
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )


def run_validator_bytes(
    record: Path, skill: str, script: str, source: str
) -> subprocess.CompletedProcess[bytes]:
    record.write_text(source, encoding="utf-8", errors="strict")
    executable = SUITE_ROOT / skill / "scripts" / script
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp936:strict"
    env["PYTHONUTF8"] = "0"
    return subprocess.run(
        [sys.executable, str(executable), str(record), "--format", "json"],
        check=False,
        capture_output=True,
        text=False,
        env=env,
    )


def run_validator_raw_bytes(
    record: Path, skill: str, script: str, source: bytes
) -> subprocess.CompletedProcess[bytes]:
    record.write_bytes(source)
    executable = SUITE_ROOT / skill / "scripts" / script
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp936:strict"
    env["PYTHONUTF8"] = "0"
    return subprocess.run(
        [sys.executable, str(executable), str(record), "--format", "json"],
        check=False,
        capture_output=True,
        text=False,
        env=env,
    )


def make_genomics_contract(
    study_mode: str, *, selection_required: bool = False
) -> dict[str, Any]:
    reference_audit = study_mode == "reference-audit"
    analysis_scale = "assembly" if reference_audit else "site"
    if study_mode == "variant-discovery":
        mapping = {
            "applicability": "applicable",
            "reason": None,
            "aligner_and_version": "synthetic-aligner 1.0",
            "caller_and_version": "synthetic-caller 1.0",
            "ploidy_assumption": "diploid autosomes",
            "callable_space": "output:callable-space-v1",
            "interval_strategy": "non-overlapping contigs with checked merge order",
            "stepwise_count_record": "output:discovery-counts-v1",
            "extensions": {},
        }
    else:
        reason = (
            "The audit verifies assembly and annotation identity without mapping reads "
            "or calling variants."
            if reference_audit
            else "The study consumes a versioned genotype call set and performs no read "
            "mapping or variant calling."
        )
        mapping = {
            "applicability": "not-applicable",
            "reason": reason,
            "aligner_and_version": None,
            "caller_and_version": None,
            "ploidy_assumption": None,
            "callable_space": None,
            "interval_strategy": None,
            "stepwise_count_record": None,
            "extensions": {},
        }

    if selection_required:
        split = {
            "applicability": "applicable",
            "reason": None,
            "split_unit": "family",
            "development_groups": ["family:development"],
            "held_out_groups": ["family:held-out"],
            "protected_from": ["threshold-selection"],
            "verification": "audit:split-membership-v1",
            "extensions": {},
        }
        selection = {
            "required": True,
            "activities": ["threshold-selection"],
            "rationale": "Threshold selection is data dependent and confined to development groups.",
            "extensions": {},
        }
    else:
        split = {
            "applicability": "not-applicable",
            "reason": "All selection-sensitive decisions are prespecified, and the estimand "
            "does not claim held-out predictive performance.",
            "split_unit": None,
            "development_groups": [],
            "held_out_groups": [],
            "protected_from": [],
            "verification": None,
            "extensions": {},
        }
        selection = {
            "required": False,
            "activities": [],
            "rationale": "All thresholds, features, covariates, and models are prespecified.",
            "extensions": {},
        }

    return {
        "schema_version": "1.1",
        "study_mode": study_mode,
        "study_id": f"study:{study_mode}",
        "biological_question": "Does the prespecified genomic proposition hold?",
        "estimand": "A prespecified contrast in the declared analysis population",
        "organism": {
            "name": "synthetic taxon",
            "ploidy": "diploid",
            "genome_history": "duplicated genome with no assumed regional effect",
            "extensions": {},
        },
        "references": [
            {
                "reference_id": "reference:one",
                "assembly_accession": "SYNTHETIC_000001",
                "assembly_version": "1.0",
                "annotation_release": "annotation-1.0",
                "coordinate_system": "1-based closed",
                "contig_naming": "assembly sequence report",
                "verification": "registry:synthetic-reference-v1",
                "extensions": {},
            }
        ],
        "samples": {
            "stable_key": "assembly_accession" if reference_audit else "sample_id",
            "inclusion_rule": "all records satisfying the prespecified eligibility rule",
            "metadata_authority": "metadata:synthetic-v1",
            "relatedness_and_groups": "not used for the assembly audit"
            if reference_audit
            else "family identifiers define dependence groups",
            "truth_roles": "registry and assembly-report cross-check"
            if reference_audit
            else "orthogonal synthetic truth subset",
            "extensions": {},
        },
        "selection_and_tuning": selection,
        "split": split,
        "analysis_scales": [analysis_scale],
        "mapping_and_variants": mapping,
        "qc_rules": [
            {
                "qc_id": "qc:one",
                "level": "reference" if reference_audit else "site",
                "metric": "registered sequence identity"
                if reference_audit
                else "versioned site quality metric",
                "rule": "match checksum and sequence dictionary"
                if reference_audit
                else "apply the prespecified eligibility rule",
                "rationale": "prevents coordinate drift"
                if reference_audit
                else "matches the analysis input contract",
                "distribution_evidence": "audit:reference-identity-v1"
                if reference_audit
                else "audit:site-quality-v1",
                "destructive": False,
                "stepwise_count_record": None,
                "extensions": {},
            }
        ],
        "hypotheses": [
            {
                "hypothesis_id": "hypothesis:one",
                "mechanism": "the audited identity is internally consistent"
                if reference_audit
                else "the prespecified genomic contrast differs from zero",
                "analysis_scale": analysis_scale,
                "proxy_or_annotation": "registry identity with documented limitations"
                if reference_audit
                else "versioned genomic annotation with documented limitations",
                "competing_explanations": ["coordinate or metadata mismatch"],
                "required_evidence_ids": ["evidence:one"],
                "status": "provisional",
                "extensions": {},
            }
        ],
        "evidence_requirements": [
            {
                "evidence_id": "evidence:one",
                "description": "A structured result that adjudicates the proposition",
                "output_ids": ["output:one"],
                "validation_ids": ["validation:one"],
                "extensions": {},
            }
        ],
        "expected_outputs": [
            {
                "output_id": "output:one",
                "description": "A structured proposition-level result table",
                "acceptance_criterion": "contains one unique row per declared analysis unit",
                "extensions": {},
            }
        ],
        "validations": [
            {
                "validation_id": "validation:one",
                "method": "check schema, unique keys, and declared analysis-unit coverage",
                "output_ids": ["output:one"],
                "acceptance_criterion": "all checks pass with no missing required unit",
                "extensions": {},
            }
        ],
        "privacy_and_publication": "synthetic public fixture with no individual data",
        "extensions": {},
    }


def workflow_state_fixture() -> dict[str, Any]:
    return {
        "schema_version": "2.0",
        "workflow_id": "workflow:revision",
        "current_state": "revision-round",
        "purpose_contract": {
            "id": "purpose:one",
            "objective": "Revise one linked package",
            "intended_contribution": "A current verified report",
            "unit_and_scale": "one report package",
            "required_outputs": ["report:one"],
            "disallowed_substitutes": [],
        },
        "authorities": {
            "design": {"id": "design:one", "location": "design.md"},
            "evidence_snapshot": {"id": "evidence:one", "location": "evidence.json"},
            "analysis_snapshot": None,
            "content_snapshot": {"id": "content:one", "location": "content.md"},
            "delivery_artifact": {
                "id": "report:one",
                "location": "report.docx",
                "sha256": "a" * 64,
            },
            "memory_status": {"id": "status:one", "location": "STATUS.md"},
        },
        "privacy_boundary": "internal synthetic fixture",
        "invalidations": [
            {
                "invalidation_id": "invalidation:report",
                "target_id": "report:one",
                "trigger_event_id": "decision:correction",
                "trigger_evidence": "decisions/correction.md",
                "reason": "An upstream correction invalidated the report",
                "previous_identity": {"identity": "report:v1", "sha256": "b" * 64},
                "critical": True,
                "status": "open",
                "required_rechecks": ["content", "package", "rendered"],
                "resolution": None,
                "waiver": None,
                "extensions": {},
            }
        ],
        "blockers": [],
        "next_action": {
            "action": "Repair the report",
            "input": "content:one",
            "expected_output": "report:one",
            "acceptance": "all required rechecks pass",
        },
        "transitions": [
            {
                "transition_id": "transition:revision",
                "from": None,
                "to": "revision-round",
                "date": "2026-08-20T12:00:00+08:00",
                "owner": "research lead",
                "evidence": ["decisions/correction.md"],
                "invalidated": ["invalidation:report"],
                "notes": "opened a linked revision",
            }
        ],
        "extensions": {},
    }


class ContractValidatorTests(unittest.TestCase):
    def test_all_validator_clis_force_utf8_and_reject_non_strict_json(self) -> None:
        with fixture_dir() as root:
            unicode_root = root / "中文 空格"
            unicode_root.mkdir()
            for skill, script in VALIDATORS:
                with self.subTest(skill=skill, case="stdout-utf8"):
                    record = unicode_root / f"{skill}.json"
                    completed = run_validator_bytes(record, skill, script, "{}")
                    stdout = completed.stdout.decode("utf-8", errors="strict")
                    stderr = completed.stderr.decode("utf-8", errors="strict")
                    self.assertEqual(completed.returncode, 1, stderr or stdout)
                    self.assertIn("中文 空格", stdout)
                    self.assertNotIn("Traceback", stderr)

                with self.subTest(skill=skill, case="duplicate-key"):
                    record = unicode_root / f"duplicate-{skill}.json"
                    completed = run_validator_bytes(
                        record, skill, script, '{"重复": 1, "重复": 2}'
                    )
                    stderr = completed.stderr.decode("utf-8", errors="strict")
                    self.assertEqual(completed.returncode, 2, stderr)
                    self.assertIn("duplicate object key", stderr)
                    self.assertIn("重复", stderr)
                    self.assertNotIn("Traceback", stderr)

                for constant in ("NaN", "Infinity", "-Infinity"):
                    with self.subTest(skill=skill, case=constant):
                        record = unicode_root / f"constant-{skill}.json"
                        completed = run_validator_bytes(
                            record, skill, script, f'{{"value": {constant}}}'
                        )
                        stderr = completed.stderr.decode("utf-8", errors="strict")
                        self.assertEqual(completed.returncode, 2, stderr)
                        self.assertIn("non-finite number", stderr)
                        self.assertNotIn("Traceback", stderr)

    def test_malformed_collection_members_never_raise_tracebacks(self) -> None:
        malformed: dict[str, dict[str, Any]] = {
            "rigorous-research-workflow": {
                "schema_version": "2.0",
                "workflow_id": "workflow:malformed",
                "current_state": [],
                "purpose_contract": {
                    "id": "purpose:one",
                    "objective": "test",
                    "intended_contribution": "test",
                    "unit_and_scale": "test",
                    "required_outputs": ["output:one"],
                },
                "authorities": {"design": {"id": "design:one", "location": "design.md"}},
                "privacy_boundary": "synthetic",
                "invalidations": [],
                "blockers": [],
                "next_action": {
                    "action": "test",
                    "input": "design:one",
                    "expected_output": "test",
                    "acceptance": "test",
                },
                "transitions": [
                    {
                        "transition_id": "transition:one",
                        "from": {},
                        "to": [],
                        "date": "2026-08-20",
                        "owner": "tester",
                        "evidence": ["design:one"],
                    }
                ],
            },
            "scientific-writing-and-revision": {
                "schema_version": "1.0",
                "document_id": "document:one",
                "document_type": "review",
                "purpose_contract": {
                    "objective": "test",
                    "intended_contribution": "test",
                    "current_document_role": "test",
                    "supporting_assets": [],
                    "deferred_deliverables": [],
                    "disallowed_substitutes": [],
                },
                "evidence_snapshot": {"id": "evidence:one", "location": "evidence.tsv"},
                "surfaces": [
                    {"surface_id": "body", "role": "body", "location": "body.md", "status": []}
                ],
                "claims": [
                    {
                        "claim_id": "claim:one",
                        "epistemic_status": {},
                        "evidence_locator": "evidence:one",
                        "surface_ids": [{}],
                    }
                ],
                "feedback_decisions": [
                    {
                        "feedback_id": "feedback:one",
                        "judgment": [],
                        "reason": "test",
                        "local_repair": "test",
                        "global_pattern": "test",
                        "verification": "test",
                        "affected_surface_ids": [[]],
                    }
                ],
                "unresolved_gaps": [],
                "next_action": "test",
            },
            "research-document-delivery": {
                "schema_version": "1.0",
                "delivery_id": "delivery:one",
                "state": {},
                "content_authority": "content:one",
                "format_authority": "format:one",
                "synchronization_direction": "single-format",
                "artifacts": [],
                "delivery_members": [{}],
                "validations": [
                    {"gate": "content", "artifact_id": {}, "status": []}
                ],
                "invalidated_checks": [],
                "unresolved_risks": [],
                "next_action": "test",
            },
            "reproducible-computational-research": {
                "schema_version": "1.0",
                "run_id": "run:one",
                "stage_id": "stage:one",
                "scientific_question": "test",
                "state": [],
                "inputs": [],
                "code": {"entrypoint": [], "version": "one", "parameters": "none"},
                "environment": {
                    "identity": "one",
                    "activation": "one",
                    "verification": "one",
                },
                "partition_contract": {
                    "unit": "file",
                    "expected_task_ids": [{}],
                    "retry_rule": "none",
                    "overwrite_rule": "never",
                },
                "outputs": [
                    {
                        "output_id": "output:one",
                        "role": "result",
                        "semantic_state": {},
                        "schema": "one",
                        "upstream_fingerprint": "one",
                        "verification": "one",
                        "path": "missing.tsv",
                    }
                ],
                "tasks": [
                    {
                        "task_id": "task:one",
                        "state": [],
                        "attempt": True,
                        "output_ids": [{}],
                        "evidence": "one",
                    }
                ],
                "checkpoints": [
                    {
                        "checkpoint_id": "checkpoint:one",
                        "task_id": {},
                        "status": [],
                        "completion_contract": "one",
                        "evidence": "one",
                    }
                ],
                "failures_and_fallbacks": [],
                "privacy_and_release": "synthetic",
                "next_action": "test",
                "extensions": {},
            },
            "genomics-study-design": {
                "schema_version": "1.0",
                "study_id": "study:one",
                "biological_question": "test",
                "estimand": "test",
                "organism": {"name": "taxon", "ploidy": "two", "genome_history": "test"},
                "references": [],
                "samples": {
                    "stable_key": "id",
                    "inclusion_rule": "all",
                    "metadata_authority": "metadata",
                    "relatedness_and_groups": "none",
                    "truth_roles": "none",
                },
                "split": {
                    "split_unit": "sample",
                    "development_groups": [{}],
                    "held_out_groups": [[]],
                    "protected_from": [{}],
                    "verification": "test",
                },
                "analysis_scales": [{}],
                "mapping_and_variants": {},
                "qc_rules": [{"qc_id": "qc:one", "level": {}, "destructive": None}],
                "hypotheses": [
                    {
                        "hypothesis_id": "hypothesis:one",
                        "mechanism": "test",
                        "analysis_scale": {},
                        "proxy_or_annotation": "test",
                        "competing_explanations": [{}],
                        "required_evidence": [[]],
                        "status": [],
                    }
                ],
                "downstream_validation": [],
                "expected_outputs": ["output:one"],
                "privacy_and_publication": "synthetic",
                "extensions": {},
            },
            "genotype-imputation-benchmarking": {
                "schema_version": "1.0",
                "benchmark_id": "benchmark:one",
                "target_use": "test",
                "optimization_object": "test",
                "population_and_ploidy": "test",
                "truth": {
                    "truth_id": "truth:one",
                    "definition": "test",
                    "split_unit": "sample",
                    "hidden_from": [{}],
                    "verification": "test",
                },
                "evaluation_universe": {
                    "authority": "one",
                    "requested_site_rule": "one",
                    "native_reported_set": None,
                    "common_evaluation_set": None,
                    "evaluable_rule": "one",
                    "missingness_rule": "one",
                },
                "conditions": [{"condition_id": "condition:one", "dimensions": {"depth": []}}],
                "workflows": [
                    {
                        "workflow_id": "workflow:one",
                        "version": "one",
                        "comparison_role": {},
                        "target_interface": [],
                        "allowed_inputs": [{}],
                        "reference_context": "none",
                        "transductive": None,
                        "tuning_budget": "none",
                        "output_fields": [[]],
                        "failure_rule": "fail",
                        "pilot_acceptance": "pass",
                        "extensions": {},
                    }
                ],
                "metrics": [
                    {
                        "metric_id": "metric:one",
                        "formula": "one",
                        "truth_representation": "one",
                        "imputed_representation": "one",
                        "unit": "site",
                        "aggregation": "one",
                        "missingness": "one",
                        "monomorphic_sites": "one",
                        "allele_frequency_source": "one",
                        "evaluation_set": [],
                    }
                ],
                "leakage_ledger": [
                    {
                        "channel_id": "channel:one",
                        "channel": "truth",
                        "control": "one",
                        "status": {},
                        "evidence": "one",
                    }
                ],
                "required_comparisons": [
                    {
                        "comparison_id": "comparison:one",
                        "workflow_ids": [{}],
                        "condition_ids": [[]],
                        "metric_ids": [{}],
                        "evaluation_sets": [[]],
                    }
                ],
                "downstream_validation": [],
                "compute_reporting": ["wall-time"],
                "extensions": {},
            },
        }
        script_by_skill = dict(VALIDATORS)
        with fixture_dir() as root:
            for skill, data in malformed.items():
                with self.subTest(skill=skill):
                    completed = run_validator(root, skill, script_by_skill[skill], data)
                    self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
                    self.assertNotIn("Traceback", completed.stderr)

    def test_workflow_state_accepts_scoped_record(self) -> None:
        with fixture_dir() as root:
            data = {
                "schema_version": "2.0",
                "workflow_id": "workflow:one",
                "current_state": "scoped",
                "purpose_contract": {
                    "id": "purpose:one",
                    "objective": "Answer a bounded question",
                    "intended_contribution": "A verified comparison",
                    "unit_and_scale": "one experiment",
                    "required_outputs": ["report:one"],
                    "disallowed_substitutes": [],
                },
                "authorities": {
                    "design": {"id": "design:one", "location": "design.md"},
                    "evidence_snapshot": None,
                    "analysis_snapshot": None,
                    "content_snapshot": None,
                    "delivery_artifact": None,
                    "memory_status": None,
                },
                "privacy_boundary": "internal synthetic fixture",
                "invalidations": [],
                "blockers": [],
                "next_action": {
                    "action": "Verify evidence",
                    "input": "design:one",
                    "expected_output": "evidence snapshot",
                    "acceptance": "all material claims have locators",
                },
                "transitions": [
                    {
                        "transition_id": "transition:one",
                        "from": None,
                        "to": "scoped",
                        "date": "2026-08-20T12:00:00+08:00",
                        "owner": "research lead",
                        "evidence": ["design:one"],
                        "invalidated": [],
                        "notes": "initial scope",
                    }
                ],
                "extensions": {},
            }
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                data,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_workflow_invalidation_contract_closes_targets_and_rechecks(self) -> None:
        with fixture_dir() as root:
            valid_open = workflow_state_fixture()
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                valid_open,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            orphan = copy.deepcopy(valid_open)
            orphan["invalidations"][0]["target_id"] = "report:missing"
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                orphan,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("unknown_invalidation_target", completed.stdout)

            advanced_with_open = copy.deepcopy(valid_open)
            advanced_with_open["current_state"] = "public-release"
            advanced_with_open["transitions"][0]["to"] = "public-release"
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                advanced_with_open,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("open_invalidation_outside_revision", completed.stdout)

            incomplete_resolution = copy.deepcopy(valid_open)
            incomplete_resolution["current_state"] = "public-release"
            incomplete_resolution["transitions"][0]["to"] = "public-release"
            invalidation = incomplete_resolution["invalidations"][0]
            invalidation["status"] = "resolved"
            invalidation["resolution"] = {
                "replacement_target_id": "report:one",
                "new_identity": "report:v2",
                "completed_rechecks": ["content", "package"],
                "evidence": ["audit/release.json"],
                "resolved_by": "research lead",
                "resolved_at": "2026-08-20T14:00:00+08:00",
            }
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                incomplete_resolution,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("missing_required_recheck", completed.stdout)

            resolved = copy.deepcopy(incomplete_resolution)
            resolved["invalidations"][0]["resolution"]["completed_rechecks"].append("rendered")
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                resolved,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            critical_waiver = copy.deepcopy(valid_open)
            critical_waiver["current_state"] = "public-release"
            critical_waiver["transitions"][0]["to"] = "public-release"
            invalidation = critical_waiver["invalidations"][0]
            invalidation["status"] = "waived"
            invalidation["waiver"] = {
                "reason": "time constraint",
                "authorized_by": "research lead",
                "decided_at": "2026-08-20T14:00:00+08:00",
                "residual_risk": "stale report",
                "evidence": "decisions/waiver.md",
            }
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                critical_waiver,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("critical_invalidation_waived", completed.stdout)

            unknown_transition = copy.deepcopy(valid_open)
            unknown_transition["transitions"][0]["invalidated"] = ["invalidation:missing"]
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                unknown_transition,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("unknown_transition_invalidation", completed.stdout)
            self.assertIn("unrecorded_invalidation_transition", completed.stdout)

            old_schema = copy.deepcopy(valid_open)
            old_schema["schema_version"] = "1.0"
            completed = run_validator(
                root,
                "rigorous-research-workflow",
                "validate_workflow_state.py",
                old_schema,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("schema_version", completed.stdout)

    def test_revision_state_rejects_unknown_surface(self) -> None:
        with fixture_dir() as root:
            data = {
                "schema_version": "1.1",
                "document_id": "document:one",
                "document_type": "review",
                "purpose_contract": {
                    "objective": "Explain a method",
                    "intended_contribution": "Bounded synthesis",
                    "current_document_role": "review evidence",
                    "supporting_assets": [],
                    "deferred_deliverables": [],
                    "disallowed_substitutes": [],
                },
                "evidence_snapshot": {"id": "evidence:one", "location": "evidence.tsv"},
                "surfaces": [
                    {
                        "surface_id": "body",
                        "role": "main argument",
                        "location": "review.md#body",
                        "status": "current",
                    }
                ],
                "claims": [
                    {
                        "claim_id": "claim:one",
                        "epistemic_status": "synthesis",
                        "evidence_locator": "evidence:one row 1",
                        "surface_ids": ["missing-surface"],
                    }
                ],
                "feedback_decisions": [],
                "unresolved_gaps": [],
                "next_action": "Repair the surface mapping",
                "extensions": {},
            }
            completed = run_validator(
                root,
                "scientific-writing-and-revision",
                "validate_revision_state.py",
                data,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("unknown_surface", completed.stdout)
            self.assertNotIn("schema_version", completed.stdout)

            data["claims"][0]["surface_ids"] = ["body"]
            completed = run_validator(
                root,
                "scientific-writing-and-revision",
                "validate_revision_state.py",
                data,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            old_schema = copy.deepcopy(data)
            old_schema["schema_version"] = "1.0"
            completed = run_validator(
                root,
                "scientific-writing-and-revision",
                "validate_revision_state.py",
                old_schema,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("schema_version", completed.stdout)

            missing_extensions = copy.deepcopy(data)
            missing_extensions.pop("extensions")
            completed = run_validator(
                root,
                "scientific-writing-and-revision",
                "validate_revision_state.py",
                missing_extensions,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("extensions", completed.stdout)

    def test_delivery_record_verifies_current_hash(self) -> None:
        with fixture_dir() as root:
            artifact = root / "report.md"
            artifact.write_text("synthetic report\n", encoding="utf-8")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            content_evidence = root / "content-audit.json"
            content_evidence.write_text('{"content":"passed"}\n', encoding="utf-8")
            content_evidence_hash = hashlib.sha256(content_evidence.read_bytes()).hexdigest()
            package_evidence = root / "delivery-package.json"
            package_evidence.write_text(
                '{"members":["report.md"]}\n', encoding="utf-8"
            )
            package_evidence_hash = hashlib.sha256(package_evidence.read_bytes()).hexdigest()

            def required_gate(gate: str) -> dict[str, Any]:
                return {"gate": gate, "evidence_mode": "file", "extensions": {}}

            def passed_gate(
                gate: str, evidence_path: str, evidence_hash: str
            ) -> dict[str, Any]:
                return {
                    "gate": gate,
                    "status": "passed",
                    "artifact_id": "artifact:report",
                    "artifact_sha256": digest,
                    "performed_at": "2026-08-20T12:00:00+08:00",
                    "evidence": {
                        "kind": "file",
                        "path": evidence_path,
                        "sha256": evidence_hash,
                        "extensions": {},
                    },
                    "not_applicable": None,
                    "limitations": "none",
                    "extensions": {},
                }

            data = {
                "schema_version": "2.0",
                "delivery_id": "delivery:one",
                "state": "final",
                "content_authority": "content:one at review.md",
                "format_authority": "format:one at report.md",
                "synchronization_direction": "single-format",
                "submitted_baseline_id": None,
                "artifacts": [
                    {
                        "artifact_id": "artifact:report",
                        "role": "final",
                        "path": "report.md",
                        "media_type": "text/markdown",
                        "sha256": digest,
                        "frozen": False,
                        "required_gates": [
                            required_gate("content"),
                            required_gate("delivery-package"),
                        ],
                        "extensions": {},
                    }
                ],
                "validations": [
                    passed_gate("content", "content-audit.json", content_evidence_hash),
                    passed_gate(
                        "delivery-package",
                        "delivery-package.json",
                        package_evidence_hash,
                    ),
                ],
                "delivery_members": ["artifact:report"],
                "invalidated_checks": [],
                "unresolved_risks": [],
                "next_action": "Send after authorization",
                "extensions": {},
            }
            completed = run_validator(
                root,
                "research-document-delivery",
                "verify_delivery_record.py",
                data,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["verdict"], "structural_pass")
            self.assertFalse(payload["delivery_completion_validated"])
            structural_text = run_validator(
                root,
                "research-document-delivery",
                "verify_delivery_record.py",
                data,
                output_format="text",
            )
            self.assertIn("RESULT: STRUCTURAL PASS", structural_text.stdout)
            self.assertNotIn("RESULT: PASS", structural_text.stdout)

            release_cases: list[tuple[str, dict[str, Any], str]] = []
            missing = copy.deepcopy(data)
            missing["validations"] = missing["validations"][:1]
            release_cases.append(
                ("missing-delivery-package", missing, "missing_required_gate_validation")
            )
            unavailable = copy.deepcopy(data)
            unavailable["validations"][0]["status"] = "unavailable"
            unavailable["validations"][0]["evidence"] = None
            release_cases.append(
                ("unavailable", unavailable, "unclosed_required_gate")
            )
            not_applicable = copy.deepcopy(data)
            not_applicable["validations"][1]["status"] = "not-applicable"
            not_applicable["validations"][1]["evidence"] = None
            not_applicable["validations"][1]["not_applicable"] = {
                "reason": "claimed unnecessary despite final handoff",
                "authorized_by": "release owner",
                "decided_at": "2026-08-20T12:30:00+08:00",
                "extensions": {},
            }
            release_cases.append(
                ("not-applicable-abuse", not_applicable, "non_waivable_release_gate")
            )
            stale = copy.deepcopy(data)
            stale["validations"][0]["artifact_sha256"] = "0" * 64
            release_cases.append(
                ("stale", stale, "stale_validation")
            )
            fabricated = copy.deepcopy(data)
            fabricated["validations"][0]["evidence"]["path"] = "invented-audit.json"
            release_cases.append(
                ("fabricated-evidence", fabricated, "missing_evidence_file")
            )
            old_schema = copy.deepcopy(data)
            old_schema["schema_version"] = "1.0"
            release_cases.append(
                ("old-schema", old_schema, "schema_version_migration")
            )
            for case, invalid, expected_code in release_cases:
                with self.subTest(case=case):
                    completed = run_validator(
                        root,
                        "research-document-delivery",
                        "verify_delivery_record.py",
                        invalid,
                    )
                    self.assertEqual(
                        completed.returncode, 1, completed.stderr or completed.stdout
                    )
                    self.assertIn(expected_code, completed.stdout)

            candidate = copy.deepcopy(data)
            candidate["state"] = "candidate"
            candidate["validations"][0]["status"] = "unavailable"
            candidate["validations"][0]["evidence"] = {
                "kind": "manual",
                "description": "content review awaits the domain owner",
                "source": "candidate handoff note",
                "extensions": {},
            }
            candidate["validations"][0]["not_applicable"] = None
            candidate_result = run_validator(
                root,
                "research-document-delivery",
                "verify_delivery_record.py",
                candidate,
            )
            self.assertEqual(
                candidate_result.returncode,
                0,
                candidate_result.stderr or candidate_result.stdout,
            )
            self.assertEqual(json.loads(candidate_result.stdout)["verdict"], "structural_pass")

    def test_delivery_record_docx_release_requires_full_gate_closure(self) -> None:
        with fixture_dir() as root:
            artifact = root / "report.docx"
            artifact.write_bytes(b"synthetic-docx-placeholder")
            digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
            evidence = root / "content-audit.json"
            evidence.write_text('{"content":"passed"}\n', encoding="utf-8")
            evidence_hash = hashlib.sha256(evidence.read_bytes()).hexdigest()
            data = {
                "schema_version": "2.0",
                "delivery_id": "delivery:docx",
                "state": "final",
                "content_authority": "content:docx",
                "format_authority": "format:docx",
                "synchronization_direction": "single-format",
                "submitted_baseline_id": None,
                "artifacts": [
                    {
                        "artifact_id": "artifact:report",
                        "role": "final",
                        "path": "report.docx",
                        "media_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        "sha256": digest,
                        "frozen": False,
                        "required_gates": [
                            {
                                "gate": "content",
                                "evidence_mode": "file",
                                "extensions": {},
                            }
                        ],
                        "extensions": {},
                    }
                ],
                "validations": [
                    {
                        "gate": "content",
                        "status": "passed",
                        "artifact_id": "artifact:report",
                        "artifact_sha256": digest,
                        "performed_at": "2026-08-20T12:00:00+08:00",
                        "evidence": {
                            "kind": "file",
                            "path": "content-audit.json",
                            "sha256": evidence_hash,
                            "extensions": {},
                        },
                        "not_applicable": None,
                        "limitations": "none",
                        "extensions": {},
                    }
                ],
                "delivery_members": ["artifact:report"],
                "invalidated_checks": [],
                "unresolved_risks": [],
                "next_action": "Complete package, render, and delivery-package gates",
                "extensions": {},
            }
            completed = run_validator(
                root,
                "research-document-delivery",
                "verify_delivery_record.py",
                data,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("missing_required_gate_contract", completed.stdout)
            self.assertIn("rendered", completed.stdout)
            self.assertIn("delivery-package", completed.stdout)

            fabricated_render = copy.deepcopy(data)
            fabricated_render["artifacts"][0]["required_gates"].extend(
                [
                    {"gate": "package", "evidence_mode": "file", "extensions": {}},
                    {"gate": "rendered", "evidence_mode": "file", "extensions": {}},
                    {
                        "gate": "delivery-package",
                        "evidence_mode": "file",
                        "extensions": {},
                    },
                ]
            )
            for gate in ("package", "delivery-package"):
                fabricated_render["validations"].append(
                    {
                        **copy.deepcopy(fabricated_render["validations"][0]),
                        "gate": gate,
                    }
                )
            fabricated_render["validations"].append(
                {
                    **copy.deepcopy(fabricated_render["validations"][0]),
                    "gate": "rendered",
                    "evidence": {
                        "kind": "file",
                        "path": "fictional-render-report.json",
                        "sha256": "0" * 64,
                        "extensions": {},
                    },
                }
            )
            render_result = run_validator(
                root,
                "research-document-delivery",
                "verify_delivery_record.py",
                fabricated_render,
            )
            self.assertEqual(render_result.returncode, 1)
            self.assertIn("missing_evidence_file", render_result.stdout)

            manual_render = copy.deepcopy(fabricated_render)
            manual_render["validations"][-1]["evidence"] = {
                "kind": "manual",
                "description": "claimed visual inspection without a captured report",
                "source": "operator assertion",
                "extensions": {},
            }
            manual_result = run_validator(
                root,
                "research-document-delivery",
                "verify_delivery_record.py",
                manual_render,
            )
            self.assertEqual(manual_result.returncode, 1)
            self.assertIn("release_requires_file_evidence", manual_result.stdout)

            waived_render = copy.deepcopy(fabricated_render)
            waived_render["validations"][-1].update(
                {
                    "status": "not-applicable",
                    "evidence": None,
                    "not_applicable": {
                        "reason": "authoritative renderer was not available",
                        "authorized_by": "release owner",
                        "decided_at": "2026-08-20T13:00:00+08:00",
                        "extensions": {},
                    },
                }
            )
            waived_result = run_validator(
                root,
                "research-document-delivery",
                "verify_delivery_record.py",
                waived_render,
            )
            self.assertEqual(waived_result.returncode, 1)
            self.assertIn("non_waivable_release_gate", waived_result.stdout)

    def test_benchmark_contract_closes_cross_references(self) -> None:
        with fixture_dir() as root:
            data = {
                "schema_version": "2.0",
                "benchmark_id": "benchmark:one",
                "target_use": "low-coverage",
                "optimization_object": "end-to-end-pipeline",
                "population_and_ploidy": "synthetic diploid population",
                "truth": {
                    "truth_id": "truth:one",
                    "definition": "orthogonal calls",
                    "split_unit": "sample",
                    "hidden_from": ["tuning", "model-selection"],
                    "verification": "synthetic audit",
                },
                "evaluation_universe": {
                    "authority": "universe:one",
                    "requested_site_rule": "all target sites",
                    "native_reported_set": True,
                    "common_evaluation_set": True,
                    "evaluable_rule": "truth and output present",
                    "missingness_rule": "report separately",
                },
                "conditions": [
                    {"condition_id": "condition:one", "dimensions": {"depth": "low"}}
                ],
                "input_registry": [
                    {
                        "input_id": "input:likelihoods",
                        "role": "target-observation",
                        "data_type": "genotype-likelihood",
                        "status": "verified",
                        "authority": "registry:synthetic-likelihoods-v1",
                        "version": "sha256:synthetic-likelihoods",
                        "contains_evaluation_truth": False,
                        "verification": "synthetic input-boundary audit",
                        "extensions": {},
                    }
                ],
                "workflows": [
                    {
                        "workflow_id": "workflow:a",
                        "version": "1.0",
                        "comparison_role": "candidate",
                        "confirmatory": True,
                        "target_interface": "genotype-likelihood",
                        "input_ids": ["input:likelihoods"],
                        "reference_context": "external-panel",
                        "transductive": False,
                        "tuning_budget": "fixed pilot",
                        "output_fields": ["GT", "DS"],
                        "failure_rule": "nonzero exit is failure",
                        "extensions": {},
                    }
                ],
                "pilot_runs": [],
                "metrics": [
                    {
                        "metric_id": "metric:r2",
                        "formula": "squared correlation",
                        "truth_representation": "GT",
                        "imputed_representation": "DS",
                        "unit": "site",
                        "aggregation": "unweighted mean",
                        "missingness": "report denominator",
                        "monomorphic_sites": "exclude and count",
                        "allele_frequency_source": "truth evaluation subset",
                        "evaluation_set": "both",
                    }
                ],
                "leakage_ledger": [
                    {
                        "channel_id": "leakage:truth",
                        "channel": "truth",
                        "control": "held out before tuning",
                        "status": "controlled",
                        "evidence": "split audit",
                    }
                ],
                "required_comparisons": [
                    {
                        "comparison_id": "comparison:one",
                        "workflow_ids": ["workflow:a"],
                        "condition_ids": ["condition:one"],
                        "metric_ids": ["metric:r2"],
                        "evaluation_sets": ["native", "common"],
                    }
                ],
                "downstream_validation": {
                    "applicability": "not-applicable",
                    "reason": "this synthetic contract tests genotype recovery only",
                    "endpoints": [],
                    "extensions": {},
                },
                "compute_reporting": ["wall-time"],
                "confirmatory_lock": {
                    "status": "open",
                    "contract_fingerprint": None,
                    "frozen_before_final_evaluation": None,
                    "evidence": None,
                },
                "extensions": {},
            }
            completed = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                data,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertIn("single_workflow", completed.stdout)
            report = json.loads(completed.stdout)
            data["pilot_runs"] = [
                {
                    "pilot_id": "pilot:workflow-a-condition-one",
                    "workflow_id": "workflow:a",
                    "condition_id": "condition:one",
                    "design_fingerprint": report["design_fingerprint"],
                    "state": "passed",
                    "output_validation": {
                        "status": "passed",
                        "verified_fields": ["GT", "DS"],
                        "evidence": "synthetic pilot audit",
                    },
                    "extensions": {},
                }
            ]
            completed = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                data,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            report = json.loads(completed.stdout)
            fingerprint = report["confirmatory_fingerprint"]
            self.assertRegex(fingerprint, r"^[0-9a-f]{64}$")

            confirmatory = copy.deepcopy(data)
            confirmatory["confirmatory_lock"] = {
                "status": "frozen",
                "contract_fingerprint": fingerprint,
                "frozen_before_final_evaluation": True,
                "evidence": "timestamped protocol freeze",
            }
            completed = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                confirmatory,
                extra_args=("--strict-confirmatory",),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            disabled_native = copy.deepcopy(data)
            disabled_native["evaluation_universe"]["native_reported_set"] = False
            completed = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                disabled_native,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("undefined_evaluation_set", completed.stdout)
            self.assertIn("undefined_metric_evaluation_set", completed.stdout)

            invalid_metric_set = copy.deepcopy(data)
            invalid_metric_set["metrics"][0]["evaluation_set"] = "union"
            completed = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                invalid_metric_set,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("invalid_metric_evaluation_set", completed.stdout)

            unaudited = copy.deepcopy(data)
            unaudited["evaluation_universe"]["native_reported_set"] = None
            unaudited["evaluation_universe"]["common_evaluation_set"] = None
            unaudited["workflows"][0]["transductive"] = None
            unaudited["workflows"][0]["output_fields"] = []
            unaudited["pilot_runs"][0]["state"] = "planned"
            unaudited["pilot_runs"][0]["design_fingerprint"] = None
            unaudited["pilot_runs"][0]["output_validation"] = {
                "status": "pending",
                "verified_fields": [],
                "evidence": None,
            }
            completed = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                unaudited,
            )
            self.assertEqual(completed.returncode, 0)
            self.assertIn("unresolved_transductive_status", completed.stdout)
            self.assertIn("unresolved_output_fields", completed.stdout)
            unaudited_strict = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                unaudited,
                extra_args=("--strict-confirmatory",),
            )
            self.assertEqual(unaudited_strict.returncode, 1)

            open_lock = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                data,
                extra_args=("--strict-confirmatory",),
            )
            self.assertEqual(open_lock.returncode, 1, open_lock.stderr or open_lock.stdout)
            self.assertIn("confirmatory_lock_open", open_lock.stdout)
            self.assertIn("missing_confirmatory_fingerprint", open_lock.stdout)

            open_leakage = copy.deepcopy(data)
            open_leakage["leakage_ledger"][0]["status"] = "open"
            stale_open = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                open_leakage,
            )
            self.assertEqual(stale_open.returncode, 1)
            stale_open_report = json.loads(stale_open.stdout)
            self.assertIn("stale_pilot_design", stale_open.stdout)
            open_leakage["pilot_runs"][0]["design_fingerprint"] = (
                stale_open_report["design_fingerprint"]
            )
            ordinary_open = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                open_leakage,
            )
            self.assertEqual(
                ordinary_open.returncode,
                0,
                ordinary_open.stderr or ordinary_open.stdout,
            )
            open_fingerprint = json.loads(ordinary_open.stdout)[
                "confirmatory_fingerprint"
            ]
            open_leakage["confirmatory_lock"] = {
                "status": "frozen",
                "contract_fingerprint": open_fingerprint,
                "frozen_before_final_evaluation": True,
                "evidence": "synthetic freeze with unresolved leakage",
            }
            strict_open = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                open_leakage,
                extra_args=("--strict-confirmatory",),
            )
            self.assertEqual(strict_open.returncode, 1, strict_open.stderr or strict_open.stdout)
            strict_open_report = json.loads(strict_open.stdout)
            open_findings = {
                finding["code"]: finding["severity"]
                for finding in strict_open_report["findings"]
            }
            self.assertEqual(open_findings["open_leakage_channel"], "error")

            changed_after_freeze = copy.deepcopy(confirmatory)
            changed_after_freeze["conditions"][0]["dimensions"]["depth"] = "changed"
            changed = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                changed_after_freeze,
                extra_args=("--strict-confirmatory",),
            )
            self.assertEqual(changed.returncode, 1, changed.stderr or changed.stdout)
            self.assertIn("confirmatory_fingerprint_mismatch", changed.stdout)

            not_prelocked = copy.deepcopy(confirmatory)
            not_prelocked["confirmatory_lock"][
                "frozen_before_final_evaluation"
            ] = False
            prelock = run_validator(
                root,
                "genotype-imputation-benchmarking",
                "validate_benchmark_contract.py",
                not_prelocked,
                extra_args=("--strict-confirmatory",),
            )
            self.assertEqual(prelock.returncode, 1, prelock.stderr or prelock.stdout)
            self.assertIn("confirmatory_conditions_not_prelocked", prelock.stdout)

    def test_templates_leave_risky_decisions_unresolved(self) -> None:
        benchmark_template = json.loads(
            (
                SUITE_ROOT
                / "genotype-imputation-benchmarking"
                / "assets"
                / "BENCHMARK_CONTRACT.json.template"
            ).read_text(encoding="utf-8", errors="strict")
        )
        self.assertEqual(benchmark_template["schema_version"], "2.0")
        universe = benchmark_template["evaluation_universe"]
        self.assertIsNone(universe["native_reported_set"])
        self.assertIsNone(universe["common_evaluation_set"])
        self.assertIsNone(benchmark_template["workflows"][0]["transductive"])
        self.assertIsNone(benchmark_template["workflows"][0]["confirmatory"])
        self.assertEqual(benchmark_template["workflows"][0]["output_fields"], [])
        self.assertEqual(benchmark_template["input_registry"][0]["status"], "open")
        self.assertIsNone(
            benchmark_template["input_registry"][0]["contains_evaluation_truth"]
        )
        self.assertEqual(benchmark_template["pilot_runs"][0]["state"], "planned")
        self.assertIsNone(
            benchmark_template["pilot_runs"][0]["design_fingerprint"]
        )
        self.assertEqual(benchmark_template["leakage_ledger"][0]["status"], "open")
        self.assertEqual(
            benchmark_template["downstream_validation"]["applicability"], "open"
        )
        self.assertEqual(benchmark_template["confirmatory_lock"]["status"], "open")
        self.assertIsNone(
            benchmark_template["confirmatory_lock"]["contract_fingerprint"]
        )
        self.assertIsNone(
            benchmark_template["confirmatory_lock"]["frozen_before_final_evaluation"]
        )

        study_template = json.loads(
            (
                SUITE_ROOT
                / "genomics-study-design"
                / "assets"
                / "STUDY_CONTRACT.json.template"
            ).read_text(encoding="utf-8", errors="strict")
        )
        self.assertEqual(study_template["schema_version"], "1.1")
        self.assertIsNone(study_template["study_mode"])
        self.assertIsNone(study_template["selection_and_tuning"]["required"])
        self.assertEqual(study_template["selection_and_tuning"]["activities"], [])
        self.assertIsNone(study_template["selection_and_tuning"]["rationale"])
        self.assertEqual(study_template["split"]["applicability"], "unresolved")
        self.assertIsNone(study_template["split"]["reason"])
        self.assertEqual(study_template["split"]["development_groups"], [])
        self.assertEqual(study_template["split"]["held_out_groups"], [])
        self.assertEqual(
            study_template["mapping_and_variants"]["applicability"], "unresolved"
        )
        self.assertIsNone(study_template["mapping_and_variants"]["reason"])
        self.assertIsNone(study_template["mapping_and_variants"]["caller_and_version"])
        self.assertIsNone(study_template["mapping_and_variants"]["callable_space"])
        self.assertIsNone(
            study_template["mapping_and_variants"]["stepwise_count_record"]
        )
        self.assertEqual(study_template["analysis_scales"], [])
        self.assertIsNone(study_template["qc_rules"][0]["destructive"])
        self.assertIsNone(study_template["qc_rules"][0]["stepwise_count_record"])
        self.assertEqual(study_template["hypotheses"][0]["required_evidence_ids"], [])
        self.assertEqual(study_template["evidence_requirements"][0]["output_ids"], [])
        self.assertEqual(
            study_template["evidence_requirements"][0]["validation_ids"], []
        )
        self.assertEqual(study_template["validations"][0]["output_ids"], [])

        run_template = json.loads(
            (
                SUITE_ROOT
                / "reproducible-computational-research"
                / "assets"
                / "RUN_MANIFEST.json.template"
            ).read_text(encoding="utf-8", errors="strict")
        )
        self.assertIsNone(run_template["outputs"][0]["completion_critical"])
        self.assertIsNone(run_template["tasks"][0]["success_marker"])
        self.assertIsNone(run_template["tasks"][0]["skip_record"])

    def test_genomics_contract_requires_declared_hypothesis_scale(self) -> None:
        with fixture_dir() as root:
            data = make_genomics_contract("association-only")
            data["hypotheses"][0]["analysis_scale"] = "window"
            completed = run_validator(
                root,
                "genomics-study-design",
                "validate_study_contract.py",
                data,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("undeclared_scale", completed.stdout)

    def test_genomics_contract_accepts_all_supported_study_modes(self) -> None:
        with fixture_dir() as root:
            for study_mode in (
                "variant-discovery",
                "existing-genotypes",
                "association-only",
                "reference-audit",
            ):
                with self.subTest(study_mode=study_mode):
                    completed = run_validator(
                        root,
                        "genomics-study-design",
                        "validate_study_contract.py",
                        make_genomics_contract(study_mode),
                    )
                    self.assertEqual(
                        completed.returncode, 0, completed.stderr or completed.stdout
                    )

    def test_genomics_variant_discovery_keeps_mapping_hard_gates(self) -> None:
        with fixture_dir() as root:
            not_applicable = make_genomics_contract("variant-discovery")
            not_applicable["mapping_and_variants"] = copy.deepcopy(
                make_genomics_contract("association-only")["mapping_and_variants"]
            )
            completed = run_validator(
                root,
                "genomics-study-design",
                "validate_study_contract.py",
                not_applicable,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("mapping_required_for_mode", completed.stdout)

            for field in (
                "caller_and_version",
                "callable_space",
                "stepwise_count_record",
            ):
                with self.subTest(missing_field=field):
                    data = make_genomics_contract("variant-discovery")
                    data["mapping_and_variants"][field] = None
                    completed = run_validator(
                        root,
                        "genomics-study-design",
                        "validate_study_contract.py",
                        data,
                    )
                    self.assertEqual(
                        completed.returncode, 1, completed.stderr or completed.stdout
                    )
                    self.assertIn(f"mapping_and_variants.{field}", completed.stdout)

    def test_genomics_not_applicable_modules_reject_sentinels_and_payloads(self) -> None:
        cases: tuple[tuple[str, Any, str], ...] = (
            ("mapping_and_variants.reason", None, "required_text"),
            ("mapping_and_variants.reason", "N/A", "non_concrete_reason"),
            (
                "mapping_and_variants.caller_and_version",
                "none",
                "inapplicable_field_present",
            ),
            ("mapping_and_variants.callable_space", "fake/path.bed", "inapplicable_field_present"),
            ("split.reason", None, "required_text"),
            ("split.reason", "no split", "non_concrete_reason"),
            ("split.development_groups", ["placeholder-group"], "inapplicable_field_present"),
            ("split.verification", "fake/audit.json", "inapplicable_field_present"),
        )
        with fixture_dir() as root:
            for dotted_path, value, expected_code in cases:
                with self.subTest(dotted_path=dotted_path, value=value):
                    data = make_genomics_contract("association-only")
                    module, field = dotted_path.split(".", maxsplit=1)
                    data[module][field] = value
                    completed = run_validator(
                        root,
                        "genomics-study-design",
                        "validate_study_contract.py",
                        data,
                    )
                    self.assertEqual(
                        completed.returncode, 1, completed.stderr or completed.stdout
                    )
                    self.assertIn(expected_code, completed.stdout)

    def test_genomics_selection_requires_isolated_and_fully_protected_split(self) -> None:
        with fixture_dir() as root:
            missing_split = make_genomics_contract("association-only")
            missing_split["selection_and_tuning"] = {
                "required": True,
                "activities": ["threshold-selection"],
                "rationale": "Threshold selection uses development data.",
                "extensions": {},
            }
            completed = run_validator(
                root,
                "genomics-study-design",
                "validate_study_contract.py",
                missing_split,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("split_required_for_selection", completed.stdout)

            unprotected = make_genomics_contract(
                "association-only", selection_required=True
            )
            unprotected["selection_and_tuning"]["activities"].append("model-selection")
            completed = run_validator(
                root,
                "genomics-study-design",
                "validate_study_contract.py",
                unprotected,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("unprotected_selection_activity", completed.stdout)

            false_with_activity = make_genomics_contract("association-only")
            false_with_activity["selection_and_tuning"]["activities"] = ["feature-selection"]
            completed = run_validator(
                root,
                "genomics-study-design",
                "validate_study_contract.py",
                false_with_activity,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("unexpected_selection_activity", completed.stdout)

    def test_genomics_no_tuning_modes_can_justify_no_split(self) -> None:
        with fixture_dir() as root:
            for study_mode in ("association-only", "reference-audit"):
                with self.subTest(study_mode=study_mode):
                    data = make_genomics_contract(study_mode)
                    self.assertEqual(data["split"]["applicability"], "not-applicable")
                    completed = run_validator(
                        root,
                        "genomics-study-design",
                        "validate_study_contract.py",
                        data,
                    )
                    self.assertEqual(
                        completed.returncode, 0, completed.stderr or completed.stdout
                    )

    def test_genomics_destructive_qc_requires_its_own_stepwise_counts(self) -> None:
        with fixture_dir() as root:
            data = make_genomics_contract("existing-genotypes")
            data["qc_rules"][0]["destructive"] = True
            completed = run_validator(
                root,
                "genomics-study-design",
                "validate_study_contract.py",
                data,
            )
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn("qc_rules[0].stepwise_count_record", completed.stdout)

            data["qc_rules"][0]["stepwise_count_record"] = "audit:qc-step-counts-v1"
            completed = run_validator(
                root,
                "genomics-study-design",
                "validate_study_contract.py",
                data,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_genomics_contract_rejects_duplicate_dangling_and_orphan_ids(self) -> None:
        cases: tuple[tuple[str, Any, str], ...] = (
            (
                "duplicate-evidence",
                lambda data: data["evidence_requirements"].append(
                    copy.deepcopy(data["evidence_requirements"][0])
                ),
                "duplicate_id",
            ),
            (
                "unknown-evidence",
                lambda data: data["hypotheses"][0].update(
                    {"required_evidence_ids": ["evidence:missing"]}
                ),
                "unknown_evidence",
            ),
            (
                "unknown-output",
                lambda data: data["evidence_requirements"][0].update(
                    {"output_ids": ["output:missing"]}
                ),
                "unknown_output",
            ),
            (
                "unknown-validation",
                lambda data: data["evidence_requirements"][0].update(
                    {"validation_ids": ["validation:missing"]}
                ),
                "unknown_validation",
            ),
            (
                "orphan-evidence",
                lambda data: data["hypotheses"][0].update(
                    {"required_evidence_ids": ["evidence:missing"]}
                ),
                "orphan_evidence",
            ),
            (
                "orphan-output",
                lambda data: data["expected_outputs"].append(
                    {
                        "output_id": "output:orphan",
                        "description": "An unused output",
                        "acceptance_criterion": "would be structured if used",
                        "extensions": {},
                    }
                ),
                "orphan_output",
            ),
            (
                "orphan-validation",
                lambda data: data["validations"].append(
                    {
                        "validation_id": "validation:orphan",
                        "method": "unused validation",
                        "output_ids": ["output:one"],
                        "acceptance_criterion": "would pass if used",
                        "extensions": {},
                    }
                ),
                "orphan_validation",
            ),
            (
                "validation-output-mismatch",
                lambda data: (
                    data["expected_outputs"].append(
                        {
                            "output_id": "output:other",
                            "description": "A second structured output",
                            "acceptance_criterion": "contains its declared row",
                            "extensions": {},
                        }
                    ),
                    data["validations"][0].update({"output_ids": ["output:other"]}),
                ),
                "validation_output_mismatch",
            ),
        )
        with fixture_dir() as root:
            for case_name, mutate, expected_code in cases:
                with self.subTest(case=case_name):
                    data = make_genomics_contract("association-only")
                    mutate(data)
                    completed = run_validator(
                        root,
                        "genomics-study-design",
                        "validate_study_contract.py",
                        data,
                    )
                    self.assertEqual(
                        completed.returncode, 1, completed.stderr or completed.stdout
                    )
                    self.assertIn(expected_code, completed.stdout)

    def test_genomics_validator_rejects_invalid_utf8_without_traceback(self) -> None:
        with fixture_dir() as root:
            completed = run_validator_raw_bytes(
                root / "invalid-utf8.json",
                "genomics-study-design",
                "validate_study_contract.py",
                b'{"study_id": "\xff"}',
            )
            stderr = completed.stderr.decode("utf-8", errors="strict")
            self.assertEqual(completed.returncode, 2, stderr)
            self.assertIn("cannot read study contract", stderr)
            self.assertNotIn("Traceback", stderr)

    def test_run_manifest_keeps_verified_zero_distinct(self) -> None:
        with fixture_dir() as root:
            source = root / "input.tsv"
            source.write_text("id\n", encoding="utf-8")
            output = root / "output.tsv"
            output.write_text("id\n", encoding="utf-8")
            entrypoint = root / "workflow.py"
            entrypoint.write_text("# synthetic entrypoint\n", encoding="utf-8")
            success_marker = root / "task-one.complete"
            success_marker.write_text("passed\n", encoding="utf-8")
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            data = {
                "schema_version": "1.0",
                "run_id": "run:one",
                "stage_id": "stage:one",
                "scientific_question": "Count qualifying records",
                "state": "complete",
                "inputs": [
                    {
                        "input_id": "input:one",
                        "role": "source",
                        "path": "input.tsv",
                        "identity": "synthetic-v1",
                        "verification": "readable table",
                    }
                ],
                "code": {
                    "entrypoint": "workflow.py",
                    "version": "synthetic-v1",
                    "parameters": "default",
                },
                "environment": {
                    "identity": "environment:v1",
                    "activation": "documented environment",
                    "verification": "version check",
                },
                "partition_contract": {
                    "unit": "file",
                    "expected_task_ids": ["task:one"],
                    "retry_rule": "retry once",
                    "overwrite_rule": "never overwrite verified output",
                },
                "tasks": [
                    {
                        "task_id": "task:one",
                        "state": "complete",
                        "attempt": 1,
                        "exit_code": 0,
                        "success_marker": "task-one.complete",
                        "skip_record": None,
                        "output_ids": ["output:one"],
                        "evidence": "log:one",
                    }
                ],
                "outputs": [
                    {
                        "output_id": "output:one",
                        "role": "authoritative result",
                        "completion_critical": True,
                        "path": "output.tsv",
                        "semantic_state": "verified-zero",
                        "sha256": digest,
                        "schema": "one header column",
                        "row_or_record_count": 0,
                        "upstream_fingerprint": "synthetic-v1",
                        "verification": "parsed zero data rows",
                    }
                ],
                "checkpoints": [
                    {
                        "checkpoint_id": "checkpoint:one",
                        "task_id": "task:one",
                        "completion_contract": "exit, schema, count, hash",
                        "status": "passed",
                        "evidence": "log:one",
                    }
                ],
                "failures_and_fallbacks": [],
                "privacy_and_release": "synthetic public fixture",
                "next_action": "Consume output:one",
                "extensions": {},
            }
            completed = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                data,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            ordinary_payload = json.loads(completed.stdout)
            self.assertEqual(ordinary_payload["validation_mode"], "structural")
            self.assertEqual(ordinary_payload["verdict"], "structural_pass")
            self.assertFalse(ordinary_payload["completion_validated"])

            ordinary_text = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                data,
                output_format="text",
            )
            self.assertEqual(
                ordinary_text.returncode,
                0,
                ordinary_text.stderr or ordinary_text.stdout,
            )
            self.assertIn("RESULT: STRUCTURAL PASS", ordinary_text.stdout)
            self.assertIn("completion was not validated", ordinary_text.stdout)
            self.assertNotIn("RESULT: PASS", ordinary_text.stdout)

            strict = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                data,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(strict.returncode, 0, strict.stderr or strict.stdout)
            strict_payload = json.loads(strict.stdout)
            self.assertEqual(strict_payload["verdict"], "complete_pass")
            self.assertTrue(strict_payload["completion_validated"])

            missing_entrypoint = copy.deepcopy(data)
            missing_entrypoint["code"]["entrypoint"] = "missing-workflow.py"
            completed = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                missing_entrypoint,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("missing_entrypoint", completed.stdout)

            duplicate_checkpoint = copy.deepcopy(data)
            duplicate_checkpoint["checkpoints"].append(
                {
                    "checkpoint_id": "checkpoint:two",
                    "task_id": "task:one",
                    "completion_contract": "second claimed completion",
                    "status": "passed",
                    "evidence": "log:two",
                }
            )
            completed = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                duplicate_checkpoint,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("duplicate_task_checkpoint", completed.stdout)

            boolean_integers = copy.deepcopy(data)
            boolean_integers["tasks"][0]["exit_code"] = False
            boolean_integers["outputs"][0]["row_or_record_count"] = False
            completed = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                boolean_integers,
            )
            self.assertEqual(completed.returncode, 1)
            self.assertIn("complete_without_success_exit", completed.stdout)
            self.assertIn("invalid_zero_state", completed.stdout)

            draft = copy.deepcopy(data)
            draft["state"] = "planned"
            draft["tasks"][0].update(
                {
                    "state": "planned",
                    "attempt": 0,
                    "exit_code": None,
                    "success_marker": None,
                    "skip_record": None,
                }
            )
            draft["outputs"][0].update(
                {
                    "path": "planned-output.tsv",
                    "semantic_state": "missing",
                    "sha256": None,
                    "row_or_record_count": None,
                }
            )
            draft["checkpoints"][0]["status"] = "pending"
            ordinary_draft = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                draft,
            )
            self.assertEqual(
                ordinary_draft.returncode,
                0,
                ordinary_draft.stderr or ordinary_draft.stdout,
            )
            strict_draft = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                draft,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                strict_draft.returncode,
                1,
                strict_draft.stderr or strict_draft.stdout,
            )
            self.assertIn("strict_complete_state", strict_draft.stdout)

            marker_not_claimed = copy.deepcopy(data)
            marker_not_claimed["tasks"][0]["success_marker"] = None
            ordinary_without_marker = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                marker_not_claimed,
            )
            self.assertEqual(
                ordinary_without_marker.returncode,
                1,
                ordinary_without_marker.stderr or ordinary_without_marker.stdout,
            )
            self.assertIn("missing_success_marker", ordinary_without_marker.stdout)
            strict_without_marker = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                marker_not_claimed,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                strict_without_marker.returncode,
                1,
                strict_without_marker.stderr or strict_without_marker.stdout,
            )
            self.assertIn("missing_success_marker", strict_without_marker.stdout)

            undecided_completion_role = copy.deepcopy(data)
            undecided_completion_role["outputs"][0]["completion_critical"] = None
            undecided = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                undecided_completion_role,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(undecided.returncode, 1, undecided.stderr or undecided.stdout)
            self.assertIn("missing_completion_critical_decision", undecided.stdout)

            missing_marker_file = copy.deepcopy(data)
            missing_marker_file["tasks"][0]["success_marker"] = "missing.complete"
            missing_marker = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                missing_marker_file,
            )
            self.assertEqual(
                missing_marker.returncode,
                1,
                missing_marker.stderr or missing_marker.stdout,
            )
            self.assertIn("missing_success_marker_file", missing_marker.stdout)

            skipped_without_record = copy.deepcopy(data)
            skipped_without_record["tasks"][0].update(
                {
                    "state": "skipped",
                    "exit_code": None,
                    "success_marker": None,
                    "skip_record": None,
                }
            )
            skipped_missing = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                skipped_without_record,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                skipped_missing.returncode,
                1,
                skipped_missing.stderr or skipped_missing.stdout,
            )
            self.assertIn("missing_skip_record", skipped_missing.stdout)

            valid_skip = copy.deepcopy(skipped_without_record)
            valid_skip["tasks"][0]["skip_record"] = {
                "reason": "current output already satisfies the checkpoint",
                "upstream_fingerprint": "synthetic-v1",
                "verification": "hash and zero-row invariant rechecked",
            }
            skipped_valid = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                valid_skip,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                skipped_valid.returncode,
                0,
                skipped_valid.stderr or skipped_valid.stdout,
            )

            mismatched_skip = copy.deepcopy(valid_skip)
            mismatched_skip["tasks"][0]["skip_record"][
                "upstream_fingerprint"
            ] = "stale-upstream"
            skipped_mismatch = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                mismatched_skip,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                skipped_mismatch.returncode,
                1,
                skipped_mismatch.stderr or skipped_mismatch.stdout,
            )
            self.assertIn("skip_upstream_identity_mismatch", skipped_mismatch.stdout)

            external_output = copy.deepcopy(data)
            external_output["outputs"][0]["path"] = "external:archive/output.tsv"
            ordinary_external = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                external_output,
            )
            self.assertEqual(
                ordinary_external.returncode,
                0,
                ordinary_external.stderr or ordinary_external.stdout,
            )
            self.assertIn("external_artifact", ordinary_external.stdout)
            strict_external = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                external_output,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                strict_external.returncode,
                1,
                strict_external.stderr or strict_external.stdout,
            )
            self.assertIn("unverifiable_external_artifact", strict_external.stdout)

            noncritical_external = copy.deepcopy(external_output)
            noncritical_external["outputs"][0]["completion_critical"] = False
            strict_noncritical = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                noncritical_external,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                strict_noncritical.returncode,
                0,
                strict_noncritical.stderr or strict_noncritical.stdout,
            )
            self.assertIn("external_artifact", strict_noncritical.stdout)

            unexpected_failed = copy.deepcopy(data)
            unexpected_failed["tasks"].append(
                {
                    "task_id": "task:unexpected-failure",
                    "state": "failed",
                    "attempt": 1,
                    "exit_code": 9,
                    "success_marker": None,
                    "skip_record": None,
                    "output_ids": ["output:one"],
                    "evidence": "log:unexpected-failure",
                }
            )
            failed_task = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                unexpected_failed,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(failed_task.returncode, 1, failed_task.stderr or failed_task.stdout)
            self.assertIn("failed_task_in_complete_run", failed_task.stdout)

            orphan_output_path = root / "orphan.tsv"
            orphan_output_path.write_text("id\nsynthetic\n", encoding="utf-8")
            orphan_output = copy.deepcopy(data)
            orphan_output["outputs"].append(
                {
                    "output_id": "output:orphan",
                    "role": "completion-critical orphan",
                    "completion_critical": True,
                    "path": "orphan.tsv",
                    "semantic_state": "produced",
                    "sha256": hashlib.sha256(orphan_output_path.read_bytes()).hexdigest(),
                    "schema": "one identifier column",
                    "row_or_record_count": 1,
                    "upstream_fingerprint": "synthetic-v1",
                    "verification": "parsed one data row",
                }
            )
            orphan = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                orphan_output,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(orphan.returncode, 1, orphan.stderr or orphan.stdout)
            self.assertIn("unreferenced_completion_critical_output", orphan.stdout)

            zero_attempt = copy.deepcopy(data)
            zero_attempt["tasks"][0]["attempt"] = 0
            invalid_attempt = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                zero_attempt,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                invalid_attempt.returncode,
                1,
                invalid_attempt.stderr or invalid_attempt.stdout,
            )
            self.assertIn("invalid_complete_attempt", invalid_attempt.stdout)

            empty_marker_path = root / "empty.complete"
            empty_marker_path.write_bytes(b"")
            empty_marker = copy.deepcopy(data)
            empty_marker["tasks"][0]["success_marker"] = "empty.complete"
            empty_marker_result = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                empty_marker,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                empty_marker_result.returncode,
                1,
                empty_marker_result.stderr or empty_marker_result.stdout,
            )
            self.assertIn("empty_success_marker", empty_marker_result.stdout)

            negative_count = copy.deepcopy(data)
            negative_count["outputs"][0]["semantic_state"] = "produced"
            negative_count["outputs"][0]["row_or_record_count"] = -1
            invalid_count = run_validator(
                root,
                "reproducible-computational-research",
                "validate_run_manifest.py",
                negative_count,
                extra_args=("--strict-complete",),
            )
            self.assertEqual(
                invalid_count.returncode,
                1,
                invalid_count.stderr or invalid_count.stdout,
            )
            self.assertIn("invalid_produced_count", invalid_count.stdout)


if __name__ == "__main__":
    unittest.main()
