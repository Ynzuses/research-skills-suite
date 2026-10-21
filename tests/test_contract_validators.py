"""Synthetic contract regression tests migrated with their owning Skills."""
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
VALIDATORS = (('rigorous-research-workflow', 'validate_workflow_state.py'), ('scientific-writing-and-revision', 'validate_revision_state.py'), ('reproducible-computational-research', 'validate_run_manifest.py'))

@contextmanager
def fixture_dir() -> Iterator[Path]:
    root = Path(__file__).resolve().parent / f'.contract-{uuid.uuid4().hex}'
    root.mkdir(parents=False, exist_ok=False)
    try:
        yield root
    finally:
        shutil.rmtree(root)

def run_validator(root: Path, skill: str, script: str, data: dict[str, Any], *, output_format: str='json', extra_args: tuple[str, ...]=()) -> subprocess.CompletedProcess[str]:
    state = root / 'record.json'
    state.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8', errors='strict')
    executable = SUITE_ROOT / skill / 'scripts' / script
    return subprocess.run([sys.executable, str(executable), str(state), '--format', output_format, *extra_args], check=False, capture_output=True, text=True, encoding='utf-8', errors='strict')

def run_validator_bytes(record: Path, skill: str, script: str, source: str) -> subprocess.CompletedProcess[bytes]:
    record.write_text(source, encoding='utf-8', errors='strict')
    executable = SUITE_ROOT / skill / 'scripts' / script
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'cp936:strict'
    env['PYTHONUTF8'] = '0'
    return subprocess.run([sys.executable, str(executable), str(record), '--format', 'json'], check=False, capture_output=True, text=False, env=env)

def workflow_state_fixture() -> dict[str, Any]:
    return {'schema_version': '2.0', 'workflow_id': 'workflow:revision', 'current_state': 'revision-round', 'purpose_contract': {'id': 'purpose:one', 'objective': 'Revise one linked package', 'intended_contribution': 'A current verified report', 'unit_and_scale': 'one report package', 'required_outputs': ['report:one'], 'disallowed_substitutes': []}, 'authorities': {'design': {'id': 'design:one', 'location': 'design.md'}, 'evidence_snapshot': {'id': 'evidence:one', 'location': 'evidence.json'}, 'analysis_snapshot': None, 'content_snapshot': {'id': 'content:one', 'location': 'content.md'}, 'delivery_artifact': {'id': 'report:one', 'location': 'report.docx', 'sha256': 'a' * 64}, 'memory_status': {'id': 'status:one', 'location': 'STATUS.md'}}, 'privacy_boundary': 'internal synthetic fixture', 'invalidations': [{'invalidation_id': 'invalidation:report', 'target_id': 'report:one', 'trigger_event_id': 'decision:correction', 'trigger_evidence': 'decisions/correction.md', 'reason': 'An upstream correction invalidated the report', 'previous_identity': {'identity': 'report:v1', 'sha256': 'b' * 64}, 'critical': True, 'status': 'open', 'required_rechecks': ['content', 'package', 'rendered'], 'resolution': None, 'waiver': None, 'extensions': {}}], 'blockers': [], 'next_action': {'action': 'Repair the report', 'input': 'content:one', 'expected_output': 'report:one', 'acceptance': 'all required rechecks pass'}, 'transitions': [{'transition_id': 'transition:revision', 'from': None, 'to': 'revision-round', 'date': '2026-08-20T12:00:00+08:00', 'owner': 'research lead', 'evidence': ['decisions/correction.md'], 'invalidated': ['invalidation:report'], 'notes': 'opened a linked revision'}], 'extensions': {}}

class ContractValidatorTests(unittest.TestCase):

    def test_all_validator_clis_force_utf8_and_reject_non_strict_json(self) -> None:
        with fixture_dir() as root:
            unicode_root = root / '中文 空格'
            unicode_root.mkdir()
            for skill, script in VALIDATORS:
                with self.subTest(skill=skill, case='stdout-utf8'):
                    record = unicode_root / f'{skill}.json'
                    completed = run_validator_bytes(record, skill, script, '{}')
                    stdout = completed.stdout.decode('utf-8', errors='strict')
                    stderr = completed.stderr.decode('utf-8', errors='strict')
                    self.assertEqual(completed.returncode, 1, stderr or stdout)
                    self.assertIn('中文 空格', stdout)
                    self.assertNotIn('Traceback', stderr)
                with self.subTest(skill=skill, case='duplicate-key'):
                    record = unicode_root / f'duplicate-{skill}.json'
                    completed = run_validator_bytes(record, skill, script, '{"重复": 1, "重复": 2}')
                    stderr = completed.stderr.decode('utf-8', errors='strict')
                    self.assertEqual(completed.returncode, 2, stderr)
                    self.assertIn('duplicate object key', stderr)
                    self.assertIn('重复', stderr)
                    self.assertNotIn('Traceback', stderr)
                for constant in ('NaN', 'Infinity', '-Infinity'):
                    with self.subTest(skill=skill, case=constant):
                        record = unicode_root / f'constant-{skill}.json'
                        completed = run_validator_bytes(record, skill, script, f'{{"value": {constant}}}')
                        stderr = completed.stderr.decode('utf-8', errors='strict')
                        self.assertEqual(completed.returncode, 2, stderr)
                        self.assertIn('non-finite number', stderr)
                        self.assertNotIn('Traceback', stderr)

    def test_malformed_collection_members_never_raise_tracebacks(self) -> None:
        malformed: dict[str, dict[str, Any]] = {'rigorous-research-workflow': {'schema_version': '2.0', 'workflow_id': 'workflow:malformed', 'current_state': [], 'purpose_contract': {'id': 'purpose:one', 'objective': 'test', 'intended_contribution': 'test', 'unit_and_scale': 'test', 'required_outputs': ['output:one']}, 'authorities': {'design': {'id': 'design:one', 'location': 'design.md'}}, 'privacy_boundary': 'synthetic', 'invalidations': [], 'blockers': [], 'next_action': {'action': 'test', 'input': 'design:one', 'expected_output': 'test', 'acceptance': 'test'}, 'transitions': [{'transition_id': 'transition:one', 'from': {}, 'to': [], 'date': '2026-08-20', 'owner': 'tester', 'evidence': ['design:one']}]}, 'scientific-writing-and-revision': {'schema_version': '1.0', 'document_id': 'document:one', 'document_type': 'review', 'purpose_contract': {'objective': 'test', 'intended_contribution': 'test', 'current_document_role': 'test', 'supporting_assets': [], 'deferred_deliverables': [], 'disallowed_substitutes': []}, 'evidence_snapshot': {'id': 'evidence:one', 'location': 'evidence.tsv'}, 'surfaces': [{'surface_id': 'body', 'role': 'body', 'location': 'body.md', 'status': []}], 'claims': [{'claim_id': 'claim:one', 'epistemic_status': {}, 'evidence_locator': 'evidence:one', 'surface_ids': [{}]}], 'feedback_decisions': [{'feedback_id': 'feedback:one', 'judgment': [], 'reason': 'test', 'local_repair': 'test', 'global_pattern': 'test', 'verification': 'test', 'affected_surface_ids': [[]]}], 'unresolved_gaps': [], 'next_action': 'test'}, 'reproducible-computational-research': {'schema_version': '1.0', 'run_id': 'run:one', 'stage_id': 'stage:one', 'scientific_question': 'test', 'state': [], 'inputs': [], 'code': {'entrypoint': [], 'version': 'one', 'parameters': 'none'}, 'environment': {'identity': 'one', 'activation': 'one', 'verification': 'one'}, 'partition_contract': {'unit': 'file', 'expected_task_ids': [{}], 'retry_rule': 'none', 'overwrite_rule': 'never'}, 'outputs': [{'output_id': 'output:one', 'role': 'result', 'semantic_state': {}, 'schema': 'one', 'upstream_fingerprint': 'one', 'verification': 'one', 'path': 'missing.tsv'}], 'tasks': [{'task_id': 'task:one', 'state': [], 'attempt': True, 'output_ids': [{}], 'evidence': 'one'}], 'checkpoints': [{'checkpoint_id': 'checkpoint:one', 'task_id': {}, 'status': [], 'completion_contract': 'one', 'evidence': 'one'}], 'failures_and_fallbacks': [], 'privacy_and_release': 'synthetic', 'next_action': 'test', 'extensions': {}}}
        script_by_skill = dict(VALIDATORS)
        with fixture_dir() as root:
            for skill, data in malformed.items():
                with self.subTest(skill=skill):
                    completed = run_validator(root, skill, script_by_skill[skill], data)
                    self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
                    self.assertNotIn('Traceback', completed.stderr)

    def test_workflow_state_accepts_scoped_record(self) -> None:
        with fixture_dir() as root:
            data = {'schema_version': '2.0', 'workflow_id': 'workflow:one', 'current_state': 'scoped', 'purpose_contract': {'id': 'purpose:one', 'objective': 'Answer a bounded question', 'intended_contribution': 'A verified comparison', 'unit_and_scale': 'one experiment', 'required_outputs': ['report:one'], 'disallowed_substitutes': []}, 'authorities': {'design': {'id': 'design:one', 'location': 'design.md'}, 'evidence_snapshot': None, 'analysis_snapshot': None, 'content_snapshot': None, 'delivery_artifact': None, 'memory_status': None}, 'privacy_boundary': 'internal synthetic fixture', 'invalidations': [], 'blockers': [], 'next_action': {'action': 'Verify evidence', 'input': 'design:one', 'expected_output': 'evidence snapshot', 'acceptance': 'all material claims have locators'}, 'transitions': [{'transition_id': 'transition:one', 'from': None, 'to': 'scoped', 'date': '2026-08-20T12:00:00+08:00', 'owner': 'research lead', 'evidence': ['design:one'], 'invalidated': [], 'notes': 'initial scope'}], 'extensions': {}}
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', data)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_workflow_invalidation_contract_closes_targets_and_rechecks(self) -> None:
        with fixture_dir() as root:
            valid_open = workflow_state_fixture()
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', valid_open)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            orphan = copy.deepcopy(valid_open)
            orphan['invalidations'][0]['target_id'] = 'report:missing'
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', orphan)
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn('unknown_invalidation_target', completed.stdout)
            advanced_with_open = copy.deepcopy(valid_open)
            advanced_with_open['current_state'] = 'public-release'
            advanced_with_open['transitions'][0]['to'] = 'public-release'
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', advanced_with_open)
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn('open_invalidation_outside_revision', completed.stdout)
            incomplete_resolution = copy.deepcopy(valid_open)
            incomplete_resolution['current_state'] = 'public-release'
            incomplete_resolution['transitions'][0]['to'] = 'public-release'
            invalidation = incomplete_resolution['invalidations'][0]
            invalidation['status'] = 'resolved'
            invalidation['resolution'] = {'replacement_target_id': 'report:one', 'new_identity': 'report:v2', 'completed_rechecks': ['content', 'package'], 'evidence': ['audit/release.json'], 'resolved_by': 'research lead', 'resolved_at': '2026-08-20T14:00:00+08:00'}
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', incomplete_resolution)
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn('missing_required_recheck', completed.stdout)
            resolved = copy.deepcopy(incomplete_resolution)
            resolved['invalidations'][0]['resolution']['completed_rechecks'].append('rendered')
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', resolved)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            critical_waiver = copy.deepcopy(valid_open)
            critical_waiver['current_state'] = 'public-release'
            critical_waiver['transitions'][0]['to'] = 'public-release'
            invalidation = critical_waiver['invalidations'][0]
            invalidation['status'] = 'waived'
            invalidation['waiver'] = {'reason': 'time constraint', 'authorized_by': 'research lead', 'decided_at': '2026-08-20T14:00:00+08:00', 'residual_risk': 'stale report', 'evidence': 'decisions/waiver.md'}
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', critical_waiver)
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn('critical_invalidation_waived', completed.stdout)
            unknown_transition = copy.deepcopy(valid_open)
            unknown_transition['transitions'][0]['invalidated'] = ['invalidation:missing']
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', unknown_transition)
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn('unknown_transition_invalidation', completed.stdout)
            self.assertIn('unrecorded_invalidation_transition', completed.stdout)
            old_schema = copy.deepcopy(valid_open)
            old_schema['schema_version'] = '1.0'
            completed = run_validator(root, 'rigorous-research-workflow', 'validate_workflow_state.py', old_schema)
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn('schema_version', completed.stdout)

    def test_revision_state_rejects_unknown_surface(self) -> None:
        with fixture_dir() as root:
            data = {'schema_version': '1.1', 'document_id': 'document:one', 'document_type': 'review', 'purpose_contract': {'objective': 'Explain a method', 'intended_contribution': 'Bounded synthesis', 'current_document_role': 'review evidence', 'supporting_assets': [], 'deferred_deliverables': [], 'disallowed_substitutes': []}, 'evidence_snapshot': {'id': 'evidence:one', 'location': 'evidence.tsv'}, 'surfaces': [{'surface_id': 'body', 'role': 'main argument', 'location': 'review.md#body', 'status': 'current'}], 'claims': [{'claim_id': 'claim:one', 'epistemic_status': 'synthesis', 'evidence_locator': 'evidence:one row 1', 'surface_ids': ['missing-surface']}], 'feedback_decisions': [], 'unresolved_gaps': [], 'next_action': 'Repair the surface mapping', 'extensions': {}}
            completed = run_validator(root, 'scientific-writing-and-revision', 'validate_revision_state.py', data)
            self.assertEqual(completed.returncode, 1)
            self.assertIn('unknown_surface', completed.stdout)
            self.assertNotIn('schema_version', completed.stdout)
            data['claims'][0]['surface_ids'] = ['body']
            completed = run_validator(root, 'scientific-writing-and-revision', 'validate_revision_state.py', data)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            old_schema = copy.deepcopy(data)
            old_schema['schema_version'] = '1.0'
            completed = run_validator(root, 'scientific-writing-and-revision', 'validate_revision_state.py', old_schema)
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn('schema_version', completed.stdout)
            missing_extensions = copy.deepcopy(data)
            missing_extensions.pop('extensions')
            completed = run_validator(root, 'scientific-writing-and-revision', 'validate_revision_state.py', missing_extensions)
            self.assertEqual(completed.returncode, 1, completed.stderr or completed.stdout)
            self.assertIn('extensions', completed.stdout)

    def test_templates_leave_risky_decisions_unresolved(self) -> None:
        run_template = json.loads((SUITE_ROOT / 'reproducible-computational-research' / 'assets' / 'RUN_MANIFEST.json.template').read_text(encoding='utf-8', errors='strict'))
        self.assertIsNone(run_template['outputs'][0]['completion_critical'])
        self.assertIsNone(run_template['tasks'][0]['success_marker'])
        self.assertIsNone(run_template['tasks'][0]['skip_record'])

    def test_run_manifest_keeps_verified_zero_distinct(self) -> None:
        with fixture_dir() as root:
            source = root / 'input.tsv'
            source.write_text('id\n', encoding='utf-8')
            output = root / 'output.tsv'
            output.write_text('id\n', encoding='utf-8')
            entrypoint = root / 'workflow.py'
            entrypoint.write_text('# synthetic entrypoint\n', encoding='utf-8')
            success_marker = root / 'task-one.complete'
            success_marker.write_text('passed\n', encoding='utf-8')
            digest = hashlib.sha256(output.read_bytes()).hexdigest()
            data = {'schema_version': '1.0', 'run_id': 'run:one', 'stage_id': 'stage:one', 'scientific_question': 'Count qualifying records', 'state': 'complete', 'inputs': [{'input_id': 'input:one', 'role': 'source', 'path': 'input.tsv', 'identity': 'synthetic-v1', 'verification': 'readable table'}], 'code': {'entrypoint': 'workflow.py', 'version': 'synthetic-v1', 'parameters': 'default'}, 'environment': {'identity': 'environment:v1', 'activation': 'documented environment', 'verification': 'version check'}, 'partition_contract': {'unit': 'file', 'expected_task_ids': ['task:one'], 'retry_rule': 'retry once', 'overwrite_rule': 'never overwrite verified output'}, 'tasks': [{'task_id': 'task:one', 'state': 'complete', 'attempt': 1, 'exit_code': 0, 'success_marker': 'task-one.complete', 'skip_record': None, 'output_ids': ['output:one'], 'evidence': 'log:one'}], 'outputs': [{'output_id': 'output:one', 'role': 'authoritative result', 'completion_critical': True, 'path': 'output.tsv', 'semantic_state': 'verified-zero', 'sha256': digest, 'schema': 'one header column', 'row_or_record_count': 0, 'upstream_fingerprint': 'synthetic-v1', 'verification': 'parsed zero data rows'}], 'checkpoints': [{'checkpoint_id': 'checkpoint:one', 'task_id': 'task:one', 'completion_contract': 'exit, schema, count, hash', 'status': 'passed', 'evidence': 'log:one'}], 'failures_and_fallbacks': [], 'privacy_and_release': 'synthetic public fixture', 'next_action': 'Consume output:one', 'extensions': {}}
            completed = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', data)
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            ordinary_payload = json.loads(completed.stdout)
            self.assertEqual(ordinary_payload['validation_mode'], 'structural')
            self.assertEqual(ordinary_payload['verdict'], 'structural_pass')
            self.assertFalse(ordinary_payload['completion_validated'])
            ordinary_text = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', data, output_format='text')
            self.assertEqual(ordinary_text.returncode, 0, ordinary_text.stderr or ordinary_text.stdout)
            self.assertIn('RESULT: STRUCTURAL PASS', ordinary_text.stdout)
            self.assertIn('completion was not validated', ordinary_text.stdout)
            self.assertNotIn('RESULT: PASS', ordinary_text.stdout)
            strict = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', data, extra_args=('--strict-complete',))
            self.assertEqual(strict.returncode, 0, strict.stderr or strict.stdout)
            strict_payload = json.loads(strict.stdout)
            self.assertEqual(strict_payload['verdict'], 'complete_pass')
            self.assertTrue(strict_payload['completion_validated'])
            missing_entrypoint = copy.deepcopy(data)
            missing_entrypoint['code']['entrypoint'] = 'missing-workflow.py'
            completed = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', missing_entrypoint)
            self.assertEqual(completed.returncode, 1)
            self.assertIn('missing_entrypoint', completed.stdout)
            duplicate_checkpoint = copy.deepcopy(data)
            duplicate_checkpoint['checkpoints'].append({'checkpoint_id': 'checkpoint:two', 'task_id': 'task:one', 'completion_contract': 'second claimed completion', 'status': 'passed', 'evidence': 'log:two'})
            completed = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', duplicate_checkpoint)
            self.assertEqual(completed.returncode, 1)
            self.assertIn('duplicate_task_checkpoint', completed.stdout)
            boolean_integers = copy.deepcopy(data)
            boolean_integers['tasks'][0]['exit_code'] = False
            boolean_integers['outputs'][0]['row_or_record_count'] = False
            completed = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', boolean_integers)
            self.assertEqual(completed.returncode, 1)
            self.assertIn('complete_without_success_exit', completed.stdout)
            self.assertIn('invalid_zero_state', completed.stdout)
            draft = copy.deepcopy(data)
            draft['state'] = 'planned'
            draft['tasks'][0].update({'state': 'planned', 'attempt': 0, 'exit_code': None, 'success_marker': None, 'skip_record': None})
            draft['outputs'][0].update({'path': 'planned-output.tsv', 'semantic_state': 'missing', 'sha256': None, 'row_or_record_count': None})
            draft['checkpoints'][0]['status'] = 'pending'
            ordinary_draft = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', draft)
            self.assertEqual(ordinary_draft.returncode, 0, ordinary_draft.stderr or ordinary_draft.stdout)
            strict_draft = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', draft, extra_args=('--strict-complete',))
            self.assertEqual(strict_draft.returncode, 1, strict_draft.stderr or strict_draft.stdout)
            self.assertIn('strict_complete_state', strict_draft.stdout)
            marker_not_claimed = copy.deepcopy(data)
            marker_not_claimed['tasks'][0]['success_marker'] = None
            ordinary_without_marker = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', marker_not_claimed)
            self.assertEqual(ordinary_without_marker.returncode, 1, ordinary_without_marker.stderr or ordinary_without_marker.stdout)
            self.assertIn('missing_success_marker', ordinary_without_marker.stdout)
            strict_without_marker = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', marker_not_claimed, extra_args=('--strict-complete',))
            self.assertEqual(strict_without_marker.returncode, 1, strict_without_marker.stderr or strict_without_marker.stdout)
            self.assertIn('missing_success_marker', strict_without_marker.stdout)
            undecided_completion_role = copy.deepcopy(data)
            undecided_completion_role['outputs'][0]['completion_critical'] = None
            undecided = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', undecided_completion_role, extra_args=('--strict-complete',))
            self.assertEqual(undecided.returncode, 1, undecided.stderr or undecided.stdout)
            self.assertIn('missing_completion_critical_decision', undecided.stdout)
            missing_marker_file = copy.deepcopy(data)
            missing_marker_file['tasks'][0]['success_marker'] = 'missing.complete'
            missing_marker = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', missing_marker_file)
            self.assertEqual(missing_marker.returncode, 1, missing_marker.stderr or missing_marker.stdout)
            self.assertIn('missing_success_marker_file', missing_marker.stdout)
            skipped_without_record = copy.deepcopy(data)
            skipped_without_record['tasks'][0].update({'state': 'skipped', 'exit_code': None, 'success_marker': None, 'skip_record': None})
            skipped_missing = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', skipped_without_record, extra_args=('--strict-complete',))
            self.assertEqual(skipped_missing.returncode, 1, skipped_missing.stderr or skipped_missing.stdout)
            self.assertIn('missing_skip_record', skipped_missing.stdout)
            valid_skip = copy.deepcopy(skipped_without_record)
            valid_skip['tasks'][0]['skip_record'] = {'reason': 'current output already satisfies the checkpoint', 'upstream_fingerprint': 'synthetic-v1', 'verification': 'hash and zero-row invariant rechecked'}
            skipped_valid = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', valid_skip, extra_args=('--strict-complete',))
            self.assertEqual(skipped_valid.returncode, 0, skipped_valid.stderr or skipped_valid.stdout)
            mismatched_skip = copy.deepcopy(valid_skip)
            mismatched_skip['tasks'][0]['skip_record']['upstream_fingerprint'] = 'stale-upstream'
            skipped_mismatch = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', mismatched_skip, extra_args=('--strict-complete',))
            self.assertEqual(skipped_mismatch.returncode, 1, skipped_mismatch.stderr or skipped_mismatch.stdout)
            self.assertIn('skip_upstream_identity_mismatch', skipped_mismatch.stdout)
            external_output = copy.deepcopy(data)
            external_output['outputs'][0]['path'] = 'external:archive/output.tsv'
            ordinary_external = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', external_output)
            self.assertEqual(ordinary_external.returncode, 0, ordinary_external.stderr or ordinary_external.stdout)
            self.assertIn('external_artifact', ordinary_external.stdout)
            strict_external = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', external_output, extra_args=('--strict-complete',))
            self.assertEqual(strict_external.returncode, 1, strict_external.stderr or strict_external.stdout)
            self.assertIn('unverifiable_external_artifact', strict_external.stdout)
            noncritical_external = copy.deepcopy(external_output)
            noncritical_external['outputs'][0]['completion_critical'] = False
            strict_noncritical = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', noncritical_external, extra_args=('--strict-complete',))
            self.assertEqual(strict_noncritical.returncode, 0, strict_noncritical.stderr or strict_noncritical.stdout)
            self.assertIn('external_artifact', strict_noncritical.stdout)
            unexpected_failed = copy.deepcopy(data)
            unexpected_failed['tasks'].append({'task_id': 'task:unexpected-failure', 'state': 'failed', 'attempt': 1, 'exit_code': 9, 'success_marker': None, 'skip_record': None, 'output_ids': ['output:one'], 'evidence': 'log:unexpected-failure'})
            failed_task = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', unexpected_failed, extra_args=('--strict-complete',))
            self.assertEqual(failed_task.returncode, 1, failed_task.stderr or failed_task.stdout)
            self.assertIn('failed_task_in_complete_run', failed_task.stdout)
            orphan_output_path = root / 'orphan.tsv'
            orphan_output_path.write_text('id\nsynthetic\n', encoding='utf-8')
            orphan_output = copy.deepcopy(data)
            orphan_output['outputs'].append({'output_id': 'output:orphan', 'role': 'completion-critical orphan', 'completion_critical': True, 'path': 'orphan.tsv', 'semantic_state': 'produced', 'sha256': hashlib.sha256(orphan_output_path.read_bytes()).hexdigest(), 'schema': 'one identifier column', 'row_or_record_count': 1, 'upstream_fingerprint': 'synthetic-v1', 'verification': 'parsed one data row'})
            orphan = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', orphan_output, extra_args=('--strict-complete',))
            self.assertEqual(orphan.returncode, 1, orphan.stderr or orphan.stdout)
            self.assertIn('unreferenced_completion_critical_output', orphan.stdout)
            zero_attempt = copy.deepcopy(data)
            zero_attempt['tasks'][0]['attempt'] = 0
            invalid_attempt = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', zero_attempt, extra_args=('--strict-complete',))
            self.assertEqual(invalid_attempt.returncode, 1, invalid_attempt.stderr or invalid_attempt.stdout)
            self.assertIn('invalid_complete_attempt', invalid_attempt.stdout)
            empty_marker_path = root / 'empty.complete'
            empty_marker_path.write_bytes(b'')
            empty_marker = copy.deepcopy(data)
            empty_marker['tasks'][0]['success_marker'] = 'empty.complete'
            empty_marker_result = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', empty_marker, extra_args=('--strict-complete',))
            self.assertEqual(empty_marker_result.returncode, 1, empty_marker_result.stderr or empty_marker_result.stdout)
            self.assertIn('empty_success_marker', empty_marker_result.stdout)
            negative_count = copy.deepcopy(data)
            negative_count['outputs'][0]['semantic_state'] = 'produced'
            negative_count['outputs'][0]['row_or_record_count'] = -1
            invalid_count = run_validator(root, 'reproducible-computational-research', 'validate_run_manifest.py', negative_count, extra_args=('--strict-complete',))
            self.assertEqual(invalid_count.returncode, 1, invalid_count.stderr or invalid_count.stdout)
            self.assertIn('invalid_produced_count', invalid_count.stdout)
if __name__ == '__main__':
    unittest.main()
