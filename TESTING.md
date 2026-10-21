# Research group testing

From the group root:

```text
python tests/validate_suite.py --root .
python -m unittest discover -s tests -p "test_*.py" -v
```

These tests cover the four owned scientific methods and the retained static, export, checksum and activation-scoring mechanisms. Contract regressions moved with genomics, workspace and document-delivery owners, and their test logic remains with those groups. Golden prompts are partitioned by target Skill; cross-group combinations are explicit optional composition cases, not automatic installation requirements.

`STATIC PASS` means bounded package checks passed. Activation-scoring tests use synthetic evidence and cannot establish model activation. The release runner's stronger mode needs a separately reviewed external trust policy and real activation evidence; grouping does not invent such approval or claim `RELEASE PASS`. See VALIDATION.md.
