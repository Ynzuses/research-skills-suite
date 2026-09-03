"""Adversarial tests for the genotype-imputation benchmark contract v2."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from typing import Any


SUITE_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = (
    SUITE_ROOT
    / "genotype-imputation-benchmarking"
    / "scripts"
    / "validate_benchmark_contract.py"
)
SCHEMA = (
    SUITE_ROOT
    / "genotype-imputation-benchmarking"
    / "assets"
    / "BENCHMARK_CONTRACT.schema.json"
)


def fingerprint(data: dict[str, Any], *, design: bool) -> str:
    excluded = {"confirmatory_lock", "pilot_runs"} if design else {"confirmatory_lock"}
    payload = {key: value for key, value in data.items() if key not in excluded}
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def freeze_lock(data: dict[str, Any]) -> None:
    data["confirmatory_lock"] = {
        "status": "frozen",
        "contract_fingerprint": fingerprint(data, design=False),
        "frozen_before_final_evaluation": True,
        "evidence": "audit:pre-evaluation-freeze-v2",
    }


def rebind_current_pilots_and_lock(data: dict[str, Any]) -> None:
    current_design = fingerprint(data, design=True)
    for pilot in data["pilot_runs"]:
        if pilot["state"] == "passed":
            pilot["design_fingerprint"] = current_design
    freeze_lock(data)


def make_confirmatory_contract() -> dict[str, Any]:
    data: dict[str, Any] = {
        "schema_version": "2.0",
        "benchmark_id": "benchmark:synthetic-v2",
        "target_use": "low-coverage",
        "optimization_object": "end-to-end-pipeline",
        "population_and_ploidy": "synthetic diploid population",
        "truth": {
            "truth_id": "truth:orthogonal-v1",
            "definition": "independent high-confidence synthetic truth",
            "split_unit": "family",
            "hidden_from": ["reference-construction", "tuning", "model-selection"],
            "verification": "audit:truth-isolation-v1",
        },
        "evaluation_universe": {
            "authority": "registry:evaluation-universe-v1",
            "requested_site_rule": "all prespecified target sites",
            "native_reported_set": True,
            "common_evaluation_set": True,
            "evaluable_rule": "truth and declared output field are both available",
            "missingness_rule": "retain missing output in availability denominator",
        },
        "conditions": [
            {
                "condition_id": "condition:one-x",
                "dimensions": {"depth": "1x", "population": "synthetic"},
            }
        ],
        "input_registry": [
            {
                "input_id": "input:target-observation-v1",
                "role": "target-observation",
                "data_type": "genotype-likelihood",
                "status": "verified",
                "authority": "registry:target-observation-v1",
                "version": "sha256:synthetic-input",
                "contains_evaluation_truth": False,
                "verification": "audit:input-boundary-v1",
                "extensions": {"synthetic": True},
            }
        ],
        "workflows": [
            {
                "workflow_id": "workflow:candidate-v1",
                "version": "candidate 1.0 sha256:synthetic",
                "comparison_role": "candidate",
                "confirmatory": True,
                "target_interface": "genotype-likelihood",
                "input_ids": ["input:target-observation-v1"],
                "reference_context": "external-panel",
                "transductive": False,
                "tuning_budget": "one prespecified development run",
                "output_fields": ["GT", "DS"],
                "failure_rule": "record failure without changing the method",
                "extensions": {},
            }
        ],
        "pilot_runs": [],
        "metrics": [
            {
                "metric_id": "metric:dosage-r2",
                "formula": "squared Pearson correlation of truth and imputed dosage",
                "truth_representation": "truth dosage",
                "imputed_representation": "DS",
                "unit": "site",
                "aggregation": "report distribution across sites",
                "missingness": "exclude missing pairs and report evaluability",
                "monomorphic_sites": "report undefined separately",
                "allele_frequency_source": "truth in held-out samples",
                "evaluation_set": "both",
            }
        ],
        "leakage_ledger": [
            {
                "channel_id": "leakage:truth",
                "channel": "truth",
                "control": "truth is isolated from all development inputs",
                "status": "controlled",
                "evidence": "audit:truth-isolation-v1",
            }
        ],
        "required_comparisons": [
            {
                "comparison_id": "comparison:primary",
                "workflow_ids": ["workflow:candidate-v1"],
                "condition_ids": ["condition:one-x"],
                "metric_ids": ["metric:dosage-r2"],
                "evaluation_sets": ["native", "common"],
            }
        ],
        "downstream_validation": {
            "applicability": "required",
            "reason": "the intended claim includes downstream association utility",
            "endpoints": [
                {
                    "endpoint_id": "endpoint:association",
                    "task": "association calibration and truth-locus recovery",
                    "role": "confirmatory",
                    "workflow_ids": ["workflow:candidate-v1"],
                    "condition_ids": ["condition:one-x"],
                    "input_fields": ["GT", "DS"],
                    "analysis_plan": "fit the prespecified model on held-out units",
                    "outcomes": [
                        {
                            "outcome_id": "outcome:calibration",
                            "definition": "genomic calibration factor",
                            "unit": "analysis",
                            "analysis_rule": "estimate from null markers",
                            "acceptance_rule": "inside the prespecified calibration interval",
                        }
                    ],
                    "status": "ready",
                    "verification": "audit:downstream-plan-freeze-v1",
                    "extensions": {},
                }
            ],
            "extensions": {},
        },
        "compute_reporting": ["wall-time", "peak-memory", "failure-rate"],
        "confirmatory_lock": {
            "status": "open",
            "contract_fingerprint": None,
            "frozen_before_final_evaluation": None,
            "evidence": None,
        },
        "extensions": {"suite_test": True},
    }
    data["pilot_runs"] = [
        {
            "pilot_id": "pilot:candidate-one-x",
            "workflow_id": "workflow:candidate-v1",
            "condition_id": "condition:one-x",
            "design_fingerprint": fingerprint(data, design=True),
            "state": "passed",
            "output_validation": {
                "status": "passed",
                "verified_fields": ["GT", "DS"],
                "evidence": "audit:pilot-output-v1",
            },
            "extensions": {},
        }
    ]
    freeze_lock(data)
    return data


def make_open_draft() -> dict[str, Any]:
    data = make_confirmatory_contract()
    data["evaluation_universe"]["native_reported_set"] = None
    data["evaluation_universe"]["common_evaluation_set"] = None
    data["input_registry"][0].update(
        {
            "status": "open",
            "authority": None,
            "version": None,
            "contains_evaluation_truth": None,
            "verification": None,
        }
    )
    data["workflows"][0].update(
        {"confirmatory": None, "transductive": None, "output_fields": []}
    )
    data["pilot_runs"] = [
        {
            "pilot_id": "pilot:planned",
            "workflow_id": "workflow:candidate-v1",
            "condition_id": "condition:one-x",
            "design_fingerprint": None,
            "state": "planned",
            "output_validation": {
                "status": "pending",
                "verified_fields": [],
                "evidence": None,
            },
            "extensions": {},
        }
    ]
    data["leakage_ledger"][0]["status"] = "open"
    data["downstream_validation"] = {
        "applicability": "open",
        "reason": None,
        "endpoints": [],
        "extensions": {},
    }
    data["confirmatory_lock"] = {
        "status": "open",
        "contract_fingerprint": None,
        "frozen_before_final_evaluation": None,
        "evidence": None,
    }
    return data


class BenchmarkContractV2Tests(unittest.TestCase):
    def run_validator(
        self,
        data: dict[str, Any],
        *,
        strict: bool = False,
        cp936: bool = False,
    ) -> tuple[subprocess.CompletedProcess[bytes], dict[str, Any]]:
        record = Path(__file__).parent / f".benchmark-确认 合同-{uuid.uuid4().hex}.json"
        try:
            record.write_text(
                json.dumps(data, ensure_ascii=False),
                encoding="utf-8",
                errors="strict",
            )
            env = os.environ.copy()
            if cp936:
                env["PYTHONIOENCODING"] = "cp936:strict"
                env["PYTHONUTF8"] = "0"
            command = [
                sys.executable,
                str(VALIDATOR),
                str(record),
                "--format",
                "json",
            ]
            if strict:
                command.append("--strict-confirmatory")
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=False,
                env=env,
            )
        finally:
            record.unlink(missing_ok=True)
        decoded = completed.stdout.decode("utf-8", errors="strict")
        report = json.loads(decoded)
        return completed, report

    def assert_code(self, report: dict[str, Any], code: str) -> None:
        self.assertIn(code, {finding["code"] for finding in report["findings"]})

    def test_schema_is_v2_without_placeholder_id(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8", errors="strict"))
        self.assertEqual(schema["properties"]["schema_version"]["const"], "2.0")
        self.assertEqual(schema["$id"], "urn:research-skills-suite:benchmark-contract:2.0")
        self.assertEqual(schema["properties"]["leakage_ledger"]["minItems"], 1)
        dimension_types = schema["$defs"]["condition"]["properties"]["dimensions"][
            "additionalProperties"
        ]["type"]
        self.assertNotIn("boolean", dimension_types)
        self.assertTrue(schema["allOf"], "downstream-analysis must have a schema guard")

    def test_valid_confirmatory_contract_passes(self) -> None:
        data = make_confirmatory_contract()
        completed, report = self.run_validator(data, strict=True)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertEqual(report["errors"], 0)
        self.assertEqual(report["design_fingerprint"], fingerprint(data, design=True))
        self.assertEqual(report["confirmatory_fingerprint"], fingerprint(data, design=False))

    def test_open_draft_passes_ordinary_but_not_strict(self) -> None:
        data = make_open_draft()
        ordinary, ordinary_report = self.run_validator(data)
        self.assertEqual(ordinary.returncode, 0, ordinary.stderr.decode("utf-8"))
        self.assertGreater(ordinary_report["warnings"], 0)
        strict, strict_report = self.run_validator(data, strict=True)
        self.assertEqual(strict.returncode, 1)
        self.assertGreater(strict_report["errors"], 0)
        self.assert_code(strict_report, "unresolved_confirmatory_role")

    def test_input_registry_closes_references_and_truth_boundary(self) -> None:
        cases: tuple[tuple[str, Any, str], ...] = (
            (
                "unknown",
                lambda data: data["workflows"][0].update({"input_ids": ["input:missing"]}),
                "unknown_input_id",
            ),
            (
                "truth-bearing",
                lambda data: data["input_registry"][0].update(
                    {"contains_evaluation_truth": True}
                ),
                "evaluation_truth_as_input",
            ),
            (
                "open",
                lambda data: data["input_registry"][0].update(
                    {
                        "status": "open",
                        "authority": None,
                        "version": None,
                        "contains_evaluation_truth": None,
                        "verification": None,
                    }
                ),
                "unclosed_input_contract",
            ),
            (
                "retired",
                lambda data: data["input_registry"][0].update({"status": "retired"}),
                "retired_input_used",
            ),
        )
        for name, mutate, expected in cases:
            with self.subTest(name=name):
                data = make_confirmatory_contract()
                mutate(data)
                rebind_current_pilots_and_lock(data)
                completed, report = self.run_validator(data, strict=True)
                self.assertEqual(completed.returncode, 1)
                self.assert_code(report, expected)

    def test_missing_or_stale_pilot_blocks_confirmation(self) -> None:
        missing = make_confirmatory_contract()
        missing["pilot_runs"] = []
        freeze_lock(missing)
        completed, report = self.run_validator(missing, strict=True)
        self.assertEqual(completed.returncode, 1)
        self.assert_code(report, "missing_current_pilot")

        stale = make_confirmatory_contract()
        stale["pilot_runs"][0]["design_fingerprint"] = "0" * 64
        freeze_lock(stale)
        completed, report = self.run_validator(stale, strict=True)
        self.assertEqual(completed.returncode, 1)
        self.assert_code(report, "stale_pilot_design")

    def test_pilot_must_validate_all_current_output_fields(self) -> None:
        data = make_confirmatory_contract()
        data["pilot_runs"][0]["output_validation"]["verified_fields"] = ["GT"]
        freeze_lock(data)
        completed, report = self.run_validator(data, strict=True)
        self.assertEqual(completed.returncode, 1)
        self.assert_code(report, "pilot_output_fields_unverified")

    def test_design_change_invalidates_pilot_and_final_lock(self) -> None:
        data = make_confirmatory_contract()
        data["conditions"][0]["dimensions"]["depth"] = "2x"
        completed, report = self.run_validator(data, strict=True)
        self.assertEqual(completed.returncode, 1)
        self.assert_code(report, "stale_pilot_design")
        self.assert_code(report, "confirmatory_fingerprint_mismatch")

    def test_downstream_endpoint_must_cover_workflow_and_real_fields(self) -> None:
        uncovered = make_confirmatory_contract()
        uncovered["downstream_validation"]["endpoints"][0]["role"] = "exploratory"
        rebind_current_pilots_and_lock(uncovered)
        completed, report = self.run_validator(uncovered, strict=True)
        self.assertEqual(completed.returncode, 1)
        self.assert_code(report, "confirmatory_workflow_without_downstream_endpoint")

        unknown_field = make_confirmatory_contract()
        unknown_field["downstream_validation"]["endpoints"][0]["input_fields"] = [
            "GT",
            "NONEXISTENT",
        ]
        rebind_current_pilots_and_lock(unknown_field)
        completed, report = self.run_validator(unknown_field, strict=True)
        self.assertEqual(completed.returncode, 1)
        self.assert_code(report, "unknown_downstream_input_field")

    def test_downstream_analysis_cannot_omit_endpoints(self) -> None:
        cases = (
            ("required", None, "missing_downstream_endpoint"),
            (
                "not-applicable",
                "claimed exemption despite downstream target",
                "downstream_target_without_validation",
            ),
            ("open", None, "unresolved_downstream_applicability"),
        )
        for applicability, reason, expected in cases:
            with self.subTest(applicability=applicability):
                data = make_confirmatory_contract()
                data["target_use"] = "downstream-analysis"
                data["downstream_validation"].update(
                    {
                        "applicability": applicability,
                        "reason": reason,
                        "endpoints": [],
                    }
                )
                rebind_current_pilots_and_lock(data)
                completed, report = self.run_validator(data, strict=True)
                self.assertEqual(completed.returncode, 1)
                self.assert_code(report, expected)

    def test_leakage_ledger_cannot_be_omitted_at_strict_gate(self) -> None:
        data = make_confirmatory_contract()
        del data["leakage_ledger"]
        rebind_current_pilots_and_lock(data)
        completed, report = self.run_validator(data, strict=True)
        self.assertEqual(completed.returncode, 1)
        self.assert_code(report, "required_list")

    def test_condition_dimensions_reject_boolean_values(self) -> None:
        data = make_confirmatory_contract()
        data["conditions"][0]["dimensions"]["depth"] = True
        rebind_current_pilots_and_lock(data)
        completed, report = self.run_validator(data)
        self.assertEqual(completed.returncode, 1)
        self.assert_code(report, "invalid_dimensions")

    def test_cp936_environment_still_emits_complete_utf8_json(self) -> None:
        data = make_confirmatory_contract()
        data["benchmark_id"] = "基准:确认性-v2"
        rebind_current_pilots_and_lock(data)
        completed, report = self.run_validator(data, strict=True, cp936=True)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode("utf-8"))
        self.assertEqual(report["errors"], 0)
        self.assertIn("确认 合同-", report["contract"])


if __name__ == "__main__":
    unittest.main()
