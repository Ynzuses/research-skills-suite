# HPC and Execution

## Environment Isolation

Install a new command-line or statistical tool in an isolated environment when its dependencies may conflict with an established pipeline. Inspect the proposed package transaction before accepting it. Do not allow an HPC script to install missing packages automatically on a compute node; fail with a clear message and install deliberately on an authorized node.

Use exact executable versions. A binary built for a newer C library may fail on cluster nodes even when it runs locally.

## Local and Cluster Roles

Place data-intensive scans, large file transformations, simulation batches, and association calculations where the data and compute resources reside. Place interactive plotting and layout iteration in a stable environment with the required visualization stack when transfer size and policy allow.

Split numeric output from rendering:

- compute stage writes TSV, array, JSON, or another stable data product;
- render stage reads that product and creates figures;
- both stages record versions and hashes.

Do not assume a package import that works on a login node works in a scheduled compute job.

## Parallelism and Resource Matching

Find the real independent unit and actual threaded section. Split independent work across jobs when possible. Measure whether CPU time divided by wall time indicates single-threaded execution despite a multi-core request.

Avoid one large allocation that runs a serial loop over many independent units. Independent jobs improve throughput, retry scope, and resource matching.

## Scheduler and Filesystem Safety

- Verify the scheduler's accepted script and argument model.
- Keep complex Python, R, Perl, or long AWK programs in separate files when scheduler preprocessing may reinterpret inline heredocs.
- On distributed filesystems, account for delayed visibility after creating wrapper or manifest files; verify or synchronize before submission.
- Use explicit success-marker files written only after all checks pass. Record a relative marker path in the task's `success_marker`; `--strict-complete` resolves it inside the manifest directory and requires a regular file for every executed complete task.
- Distinguish scheduler submission success from job execution success.

## Wall-Time Diagnosis

When an exit code or resource summary suggests a wall-time limit:

1. compare observed wall and CPU time with the requested limit;
2. inspect whether the log ends mid-operation without a traceback;
3. account for I/O, parsing, sorting, statistical transforms, serialization, and cleanup, not just the visible main loop;
4. estimate from a representative measured unit and add justified margin;
5. only then investigate code defects.

## Path Verification

Verify real directories and files with direct listing or exact search before diagnosing absence. Do not infer paths from script names, comments, remembered layouts, or job names. Log filenames often come from scheduler headers rather than the worker filename.

For skip or restart guards, combine file presence with content completeness and lineage, such as last expected unit, row count, and timestamp or upstream hash.
