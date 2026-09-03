# Deterministic Bootstrap Manifest Contract

## What the Helper Owns

The bootstrap helper makes an already approved control-plane plan repeatable. It does not infer a workspace profile, choose directory ownership, decide which Skills are relevant, or approve its own writes. Those semantic decisions remain in the read-only discovery, blueprint, and authorization stages.

Use the helper only after the proposed blueprint names the exact directories, rendered control-plane files, frozen boundaries, and real instruction entry. Start from `assets/BOOTSTRAP_MANIFEST.json.template`; validate its shape against `assets/BOOTSTRAP_MANIFEST.schema.json`. The template is deliberately pending and non-executable.

## Required Approval State

An executable manifest has:

- `schema_version` equal to `1`;
- `approval.state` equal to `approved`;
- a non-empty decision ID, approving role, and time-zone-aware ISO 8601 approval time;
- `approval.manifest_sha256` equal to the SHA-256 of the complete canonical JSON manifest after setting only that self-referential field to `null`; canonical JSON uses UTF-8, sorted keys, no insignificant whitespace, non-ASCII characters unescaped, and no non-finite numbers;
- `workspace.root` equal to `.` so the command-line root remains authoritative;
- `workspace.root_identity` bound to the resolved root's normalized-path SHA-256, device, and inode reported by `--inspect-root`;
- `workspace.frozen_inventory_complete` equal to `true` after read-only boundary discovery;
- every known frozen or read-only relative path in `workspace.frozen_paths`;
- exact rendered UTF-8 content and lowercase SHA-256 for each selected file and the managed entry block.

Changing `pending` to `approved` is a record of authority, not a substitute for authority. Do it only when the current task or an existing workspace rule authorizes the exact create-and-merge plan.

Inspect the root before finalizing approval metadata:

```text
python scripts/apply_workspace_bootstrap.py --root workspace-root --inspect-root
```

Copy the reported identity exactly. Fill every other manifest field, leave `approval.manifest_sha256` as `null`, calculate the canonical hash defined above, then store that digest in the field. Any later semantic manifest edit requires a new digest and renewed approval. The resolved root identity must still match at dry-run and before every apply operation.

## Allowed Plan

`directories` lists every missing parent directory the helper may create. `files` lists Markdown control-plane files with one typed role. A file is created only when missing; an existing byte-identical file is a no-op, and any other existing content is a conflict.

`entry` identifies the actual discoverable Markdown instruction file. The helper may create it only when `create_if_missing` is true. Otherwise it constructs the original bytes plus one block bounded by the fixed markers:

```text
<!-- manage-workspace-memory:managed-block:start -->
...
<!-- manage-workspace-memory:managed-block:end -->
```

Existing line endings are preserved. Exactly one identical block is a no-op. Partial, repeated, nested, embedded, or different managed markers are conflicts; the helper never edits them in place.

Before reading or writing an existing file, the helper binds its device/inode identity, content state, single-link count, and parent-directory identity chain. It rejects hard-linked files (`st_nlink != 1`) and any symbolic-link, junction, or other reparse component. It rechecks these bindings before and after opens and writes. For an approved entry merge, it writes the complete post-merge bytes to an exclusive temporary file in the same directory, verifies that file and the original entry again, then atomically promotes the temporary file over the still-bound entry. This avoids mutating a hard-link alias and limits interrupted writes to an inspectable temporary artifact.

## Forbidden Plan

The helper rejects:

- absolute, drive-qualified, backslash, parent-traversal, NUL, or root targets;
- writes through symbolic links, junctions, reparse points, hard-linked files, changed parent identities, or into declared frozen paths;
- undeclared parent-directory creation;
- non-Markdown control files, duplicate targets, role values outside the schema, and content-hash mismatch;
- version-control metadata, hooks, workflow/scheduler locations, or cache/environment internals;
- any existing non-identical control file or entry block.

It has no operation to move or delete user assets, overwrite existing control-plane files, use the network or subprocesses, invoke Git, install watchers/hooks/schedulers, use cloud services, commit, push, or publish. Its only replacement operation is the verified same-directory promotion described above for the exact approved instruction entry; its own temporary file is not a user asset. A plan needing any other mutation stops outside this helper for separate review and authority.

## Run and Verify

Default execution is a read-only dry run:

```text
python scripts/apply_workspace_bootstrap.py --root workspace-root --manifest approved-manifest.json
```

Review the JSON change manifest, especially the root identity, approved manifest digest, exact targets and bound identities, conflicts, predicted post-write hashes, and `plan_sha256`. Apply only after that review. To bind apply to those exact dry-run observations, pass the reviewed plan digest:

```text
python scripts/apply_workspace_bootstrap.py --root workspace-root --manifest approved-manifest.json --apply --expected-plan-sha256 reviewed-plan-sha256
```

The plan-hash guard is optional so an explicitly authorized one-step local apply remains possible, but release and unattended procedures should use it. A changed root, manifest, file inode, parent identity, pre-write content, or planned operation changes the digest and stops before writes.

The success report distinguishes existing, planned, created, and merged objects and records bound identities plus pre-write, planned post-write, and observed post-write SHA-256 values. Run a new dry run after successful apply, then apply its new no-change plan or run apply without the old plan digest: it must report only existing or unchanged objects and leave every byte identical. An old pre-apply plan digest intentionally no longer matches post-apply state. Then run the workspace audit and a fresh-session routing test. Neither a successful apply nor a successful structural audit proves that the blueprint's authority decisions are semantically correct.

Every error is JSON and includes `persisted_changes`, `recovery_required`, and `writes_started`. If apply fails after a declared creation, atomic replacement, or exclusive-temp creation reached disk, stop and reconcile those exact paths. A retained exclusive temp is never silently retried or deleted by the helper. Verify identities and hashes first; perform any cleanup or rollback as a separate authorized action.

## Stop Conditions

Stop without retrying or editing around the helper when it reports a conflict, approval/root/plan digest mismatch, incomplete frozen inventory, changed identity or content hash, non-single link count, ambiguous managed block, symbolic-link/junction/reparse component, missing undeclared parent, target outside the root, or a non-empty recovery list. Re-inventory the workspace and revise the proposed blueprint; obtain renewed approval if any target or rendered content changes.
