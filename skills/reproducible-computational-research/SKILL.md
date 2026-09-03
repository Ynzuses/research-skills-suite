---
name: reproducible-computational-research
description: "Design, diagnose, and hand off reproducible local or HPC research workflows. Use when a task needs provenance, environments, parallel tasks, checkpoints, idempotent reruns, missing-versus-zero results, scheduler failures, single-source outputs, artifact audits, or public-code boundaries. Do not use for ordinary application debugging."
---

# Reproducible Computational Research

## Purpose

Build computational research in which every result has an authoritative input, explicit transformation, inspectable output, recoverable failure path, and defensible handoff. Treat data, code, runtime environment, workflow state, and narrative as separate evidence layers.

## Establish the Computational Contract

Record:

- scientific question and unit of analysis;
- authoritative inputs and immutable identifiers or hashes;
- expected outputs and schema;
- local, cluster, and external execution boundaries;
- software versions and environments;
- parallelization unit, resources, and wall-time basis;
- checkpoint, failure, retry, fallback, and rollback rules;
- privacy and publication boundaries.

Do not start with a desired result or figure shape. Before data are verified, define schemas, invariants, and analysis plans only.

For a durable stage, instantiate [RUN_MANIFEST.json.template](assets/RUN_MANIFEST.json.template). Use one manifest to distinguish planned, running, complete, failed, partial, stale, and verified-zero states; do not encode those meanings in filenames alone. Validate its structural and file/hash closure read-only:

```text
python scripts/validate_run_manifest.py run-manifest.json
```

Project-specific scheduler fields may live under `extensions`. The validator cannot prove a scientific result or scheduler success; it checks that the claimed state has the required evidence and current artifact identities.

Use ordinary validation while a run is planned, active, partial, failed, or stale. Before declaring a run complete or handing it off as final, run:

```text
python scripts/validate_run_manifest.py run-manifest.json --strict-complete
```

Strict completion requires `state=complete`, an exact match between declared and observed task IDs, no failed task, at least one recorded attempt for every executed complete task, an explicit `completion_critical` decision for every output, a non-empty locally verifiable success-marker file for every executed complete task, and a structured `skip_record` for every skipped task. Every completion-critical output must be owned by at least one task. The skip record must state the reason, the exact upstream fingerprint, and verification evidence; its fingerprint must match every reused output, which must already be produced or verified-zero. A produced or verified-zero output behind an `external:` locator remains usable during ordinary planning and recovery, but blocks strict completion when `completion_critical=true` because this local validator cannot verify its bytes. An explicitly noncritical external diagnostic may remain a warning. Ordinary validation reports structural consistency only and must not be cited as completion evidence.

## Run the Workflow

### 1. Make the Data Model Explicit

Define keys, units, denominators, missing-value semantics, zero-result semantics, aggregation rules, and authoritative files. When two files contain a similarly named metric, compare definitions and trace published numbers back to the generating table or script rather than choosing by filename.

Read [workflow-and-provenance.md](references/workflow-and-provenance.md) for artifact contracts and evidence layers.

### 2. Freeze Environments and Interfaces

Use isolated environments for tools with conflicting dependencies. Record exact executable versions and paths or activation instructions. Verify required imports and commands in the actual execution environment, not only on a login node or development machine.

### 3. Partition Independent Work

Split independent samples, intervals, chromosomes, simulations, folds, or files into independent jobs or tasks when safe. Match requested resources to the true parallelism of the tool. A thread-count option may accelerate input reading without parallelizing the main algorithm.

Read [hpc-and-execution.md](references/hpc-and-execution.md) for schedulers, wall time, path verification, distributed filesystems, and local/HPC division.

### 4. Add Idempotent Checkpoints

Each task should validate prerequisites, create outputs in a controlled location, fail loudly on violated invariants, and become safely skippable only after a completion contract passes. File existence alone is rarely sufficient; use content, terminal record, count, timestamp or upstream version, and an explicit success marker where appropriate.

### 5. Execute Before Narrating

Run the analysis or inspect authoritative outputs before writing quantitative conclusions. Keep exploratory outputs distinct from confirmatory or publication outputs. Generate final tables and figures from a single reproducible path rather than mixing partial log extraction with ad hoc recomputation.

### 6. Diagnose from the Lowest Reliable Layer

When a task fails, inspect scheduler state, exit code, resource usage, stderr, logs, actual paths, environment, input invariants, and output completeness before proposing a scientific explanation. “Job finished” is not the same as “all outputs are complete.”

Read [failure-recovery-and-release.md](references/failure-recovery-and-release.md) for hypothesis-based diagnosis, reruns, fallbacks, code review, and release boundaries.

### 7. Quantify Handoffs

For every completed stage, report evidence such as file count, row count, schema, last expected unit, timestamps, hashes, completion markers, and a sample of invariant checks. A qualitative “done” message is not a sufficient handoff for a large workflow.

### 8. Review and Release Deliberately

Review new scientific code, statistical decisions, HPC scripts, and formal figures independently when possible. Separate:

- internal working code;
- reproducibility or archival code;
- code supplied to a collaborator or supervisor;
- public release code.

These artifacts have different inclusion, privacy, portability, documentation, and licensing requirements.

## Non-Negotiable Rules

- Data precede narrative.
- Software defaults are part of the experimental design; make consequential ones explicit.
- A missing file is not a biological zero, and a zero-row result is not necessarily a failed task.
- Do not infer twice from a summary when the underlying log or artifact is available.
- Do not overwrite an existing result without checking its provenance, downstream references, and rollback path.
- Do not create final academic output by combining partial historical logs with unrecorded live computation.
- Inspect ignored or untracked output directories directly; Git status is not an inventory.
- Batch code rewrites require structural guards and syntax or AST validation.
- Public sanitization must not destroy scientific logic or remove useful analysis merely to hide development history.

## Stop or Ask When

Pause when a fallback changes the scientific question or estimand, a rerun will overwrite an irreplaceable result without recovery, external execution requires user authority, private data would leave the approved boundary, or competing authoritative inputs cannot be reconciled.

## Completion Standard

A computational stage is complete when the run manifest closes, authoritative inputs, code, environment, execution record, outputs, and checks form one reproducible chain; missing, partial, stale, failed, and verified-zero states remain distinct; failures and reruns are explainable; handoff evidence is quantitative; and any public or archival artifact matches its stated purpose and privacy boundary.
