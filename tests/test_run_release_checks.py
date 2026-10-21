"""Adversarial tests for the hash-bound release runner trust boundary."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUNNER = HERE / "run_release_checks.py"
SKILLS = (
    "evidence-traceable-literature-review",
    "reproducible-computational-research",
    "rigorous-research-workflow",
    "scientific-writing-and-revision",
)
PASS_MARKER = "RESULT: TRUSTED TECHNICAL RELEASE GATE PASS"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", errors="strict", newline="\n")


class ReleaseFixture:
    def __init__(self, *, static_script: str | None = None) -> None:
        self.base = HERE / f".release-runner-{uuid.uuid4().hex}"
        self.candidate = self.base / "candidate"
        self.trusted = self.base / "trusted"
        self.installed = self.base / "installed"
        self.evidence = self.base / "evidence"
        self.validators = self.base / "validators"
        self.policy = self.base / "trust-policy.json"
        self.base.mkdir()

        for name in SKILLS:
            write(
                self.candidate / "skills" / name / "SKILL.md",
                f"---\nname: {name}\ndescription: Synthetic fixture.\n---\n",
            )
        write(
            self.candidate / ".codex-plugin" / "plugin.json",
            '{"name":"fixture","version":"0.0.0"}\n',
        )
        write(
            self.candidate / "tests" / "validate_suite.py",
            "raise SystemExit('CANDIDATE STATIC MUST NOT RUN')\n",
        )
        write(
            self.candidate / "tests" / "score_activation_results.py",
            "raise SystemExit('CANDIDATE SCORER MUST NOT RUN')\n",
        )
        write(
            self.candidate / "tests" / "test_candidate_fake.py",
            "raise AssertionError('CANDIDATE TEST MUST NOT RUN')\n",
        )

        (self.trusted / "tests").mkdir(parents=True)
        shutil.copyfile(RUNNER, self.trusted / "tests" / RUNNER.name)
        write(
            self.trusted / "tests" / "validate_suite.py",
            static_script or "print('trusted static')\n",
        )
        write(
            self.trusted / "tests" / "score_activation_results.py",
            """import sys
required = {
    '--candidate-root', '--installed-root', '--evidence-manifest',
    '--min-precision', '--min-recall', '--min-exact-routing',
    '--min-skill-precision', '--min-skill-recall',
    '--min-class-exact-routing'
}
missing = sorted(required - set(sys.argv))
if missing:
    raise SystemExit('missing scorer arguments: ' + repr(missing))
print('{}')
""",
        )
        write(self.trusted / "tests" / "golden-prompts.tsv", "fixture\n")
        write(
            self.trusted / "tests" / "test_smoke.py",
            "import unittest\n\nclass Smoke(unittest.TestCase):\n"
            "    def test_trusted(self):\n        self.assertTrue(True)\n",
        )
        write(self.validators / "skill.py", "print('trusted Skill validator')\n")
        write(self.validators / "plugin.py", "print('trusted Plugin validator')\n")
        write(self.evidence / "results.tsv", "fixture\n")
        write(self.evidence / "manifest.json", "{}\n")
        shutil.copytree(self.candidate, self.installed)

    @property
    def runner(self) -> Path:
        return self.trusted / "tests" / "run_release_checks.py"

    def base_command(self, *, runner: Path | None = None) -> list[str]:
        return [
            sys.executable,
            str(runner or self.runner),
            "--root",
            str(self.candidate),
            "--trusted-root",
            str(self.trusted),
            "--official-validator",
            str(self.validators / "skill.py"),
            "--plugin-validator",
            str(self.validators / "plugin.py"),
            "--activation-results",
            str(self.evidence / "results.tsv"),
            "--installed-root",
            str(self.installed),
            "--evidence-manifest",
            str(self.evidence / "manifest.json"),
            "--timeout",
            "30",
        ]

    def run(self, *extra: str, runner: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*self.base_command(runner=runner), *extra],
            cwd=self.base,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            timeout=60,
        )

    def draft(self) -> subprocess.CompletedProcess[str]:
        return self.run("--write-trust-policy-draft", str(self.policy))

    def approve(self) -> None:
        payload = json.loads(self.policy.read_text(encoding="utf-8", errors="strict"))
        payload["status"] = "approved"
        payload["approval"] = {
            "approver": "fixture-maintainer",
            "approved_at": "2026-08-20T12:00:00+08:00",
        }
        self.policy.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            errors="strict",
            newline="\n",
        )

    def release(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.run("--release", "--trust-policy", str(self.policy), *extra)

    def close(self) -> None:
        shutil.rmtree(self.base)


class ReleaseRunnerTrustTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixtures: list[ReleaseFixture] = []

    def fixture(self, **kwargs: str) -> ReleaseFixture:
        fixture = ReleaseFixture(**kwargs)
        self.fixtures.append(fixture)
        return fixture

    def tearDown(self) -> None:
        for fixture in reversed(self.fixtures):
            fixture.close()

    def assert_blocked(self, completed: subprocess.CompletedProcess[str]) -> None:
        output = completed.stdout + completed.stderr
        self.assertNotEqual(completed.returncode, 0, output)
        self.assertNotIn(PASS_MARKER, output)

    def approved_fixture(self, **kwargs: str) -> ReleaseFixture:
        fixture = self.fixture(**kwargs)
        drafted = fixture.draft()
        self.assertEqual(drafted.returncode, 0, drafted.stdout + drafted.stderr)
        fixture.approve()
        return fixture

    def test_hash_consistent_external_trust_root_passes(self) -> None:
        fixture = self.approved_fixture()
        completed = fixture.release()
        output = completed.stdout + completed.stderr
        self.assertEqual(completed.returncode, 0, output)
        self.assertIn(PASS_MARKER, output)
        self.assertNotIn("CANDIDATE STATIC MUST NOT RUN", output)
        self.assertNotIn("CANDIDATE SCORER MUST NOT RUN", output)
        self.assertNotIn("CANDIDATE TEST MUST NOT RUN", output)
        self.assertIn("not a cryptographic signature", output)

    def test_pending_policy_is_not_approval(self) -> None:
        fixture = self.fixture()
        self.assertEqual(fixture.draft().returncode, 0)
        self.assert_blocked(fixture.release())

    def test_validator_inside_candidate_is_rejected(self) -> None:
        fixture = self.fixture()
        command = fixture.base_command()
        index = command.index("--official-validator") + 1
        command[index] = str(fixture.candidate / "tests" / "validate_suite.py")
        completed = subprocess.run(
            [*command, "--write-trust-policy-draft", str(fixture.policy)],
            cwd=fixture.base,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
        )
        self.assert_blocked(completed)

    def test_validator_hash_change_is_rejected(self) -> None:
        fixture = self.approved_fixture()
        write(fixture.validators / "skill.py", "print('changed')\n")
        self.assert_blocked(fixture.release())

    def test_threshold_floor_and_policy_cli_mismatch_are_rejected(self) -> None:
        fixture = self.approved_fixture()
        with self.subTest("below hard floor"):
            self.assert_blocked(fixture.release("--min-precision", "0.94"))
        payload = json.loads(fixture.policy.read_text(encoding="utf-8"))
        payload["thresholds"]["min_precision"] = 0.99
        fixture.policy.write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        with self.subTest("policy differs from CLI"):
            self.assert_blocked(fixture.release())

    def test_candidate_mutation_after_stage_is_rejected(self) -> None:
        static = """import argparse
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--root', required=True)
args, _ = p.parse_known_args()
Path(args.root, 'stage-tamper.txt').write_text('tampered', encoding='utf-8')
print('mutated')
"""
        fixture = self.approved_fixture(static_script=static)
        self.assert_blocked(fixture.release())

    def test_non_utf8_child_output_is_rejected(self) -> None:
        static = "import sys\nsys.stdout.buffer.write(bytes([255]))\n"
        fixture = self.approved_fixture(static_script=static)
        self.assert_blocked(fixture.release())

    def test_each_trusted_code_identity_change_is_rejected(self) -> None:
        cases = (
            "tests/run_release_checks.py",
            "tests/test_smoke.py",
            "tests/golden-prompts.tsv",
            "tests/score_activation_results.py",
        )
        for relative in cases:
            with self.subTest(relative=relative):
                fixture = self.approved_fixture()
                path = fixture.trusted.joinpath(*relative.split("/"))
                path.write_bytes(path.read_bytes() + b"\n# changed\n")
                self.assert_blocked(fixture.release())

    def test_nested_roots_and_policy_are_rejected(self) -> None:
        with self.subTest("installed under candidate"):
            fixture = self.fixture()
            nested = fixture.candidate / "nested-installed"
            nested.mkdir()
            command = fixture.base_command()
            command[command.index("--installed-root") + 1] = str(nested)
            completed = subprocess.run(
                [*command, "--write-trust-policy-draft", str(fixture.policy)],
                cwd=fixture.base,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
            )
            self.assert_blocked(completed)
        with self.subTest("policy under candidate"):
            fixture = self.fixture()
            completed = fixture.run(
                "--write-trust-policy-draft",
                str(fixture.candidate / "policy.json"),
            )
            self.assert_blocked(completed)
        with self.subTest("trusted root under candidate"):
            fixture = self.fixture()
            nested_trusted = fixture.candidate / "trusted"
            shutil.copytree(fixture.trusted, nested_trusted)
            command = fixture.base_command(runner=nested_trusted / "tests" / RUNNER.name)
            command[command.index("--trusted-root") + 1] = str(nested_trusted)
            completed = subprocess.run(
                [*command, "--write-trust-policy-draft", str(fixture.policy)],
                cwd=fixture.base,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="strict",
            )
            self.assert_blocked(completed)


if __name__ == "__main__":
    unittest.main()
