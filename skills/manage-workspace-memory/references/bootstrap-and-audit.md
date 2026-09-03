# Bootstrap and Audit

## Choose Bootstrap or Refactor

For a new workspace, create the smallest sufficient role set and connect it to the startup entry. For an existing workspace, inventory first and map current files to roles. Refactor only after distinguishing:

- missing responsibility;
- duplicated authority;
- stale route;
- mixed lifecycle;
- naming preference with no functional defect.

A different filename or directory scheme is not itself a defect.

## Read-Only Inventory

Before writing, collect:

1. applicable agent or collaborator rules;
2. README and project-management entry points;
3. memory, status, design, index, history, DAG, and audit files;
4. active project directories and frozen archives;
5. authoritative data, code, document, and result locations;
6. version-control and ignore boundaries;
7. local-only, private, generated, or externally stored assets;
8. broken links, missing targets, duplicated names, and contradictory status claims.

Inspect physical artifacts where the inventory affects decisions. Preserve unrelated changes in a dirty workspace.

## Four-Phase Build Procedure

### 1. Discover read-only

Inventory the workspace and characterize:

- projects, research questions, products, and deliverables;
- authority owners and teams;
- shared versus project-specific assets;
- active, generated, cached, externally owned, and frozen lifecycles;
- privacy, version-control, publication, and write boundaries;
- local, remote, container, or HPC execution roots;
- existing entry points and coherent conventions worth preserving.

Do not create directories during discovery.

### 2. Propose a blueprint and difference plan

1. Infer lean, standard, or federated architecture from the characteristics above.
2. Assign each fact type and authoritative asset to one owning scope.
3. Map existing paths to needed roles before proposing new names.
4. List exact keep, create, link, merge, move, retire, and unresolved actions with reasons.
5. Separate safe control-plane creation from high-impact asset moves or governance changes that need confirmation.
6. Inventory the Skills or equivalent capabilities actually available in the current environment, match only relevant capabilities to observed project task types, and propose a discoverable route table with explicit composition and exclusion boundaries.
7. When safe control-plane creation should be repeatable, render an exact pending manifest from `assets/BOOTSTRAP_MANIFEST.json.template`: list only selected missing directories and Markdown control files, the real instruction entry and managed-block content, the complete frozen-path inventory, and SHA-256 for every rendered payload.

Use `assets/WORKSPACE_BLUEPRINT.md.template` when the reasoning must persist.
The manifest is a mechanical projection of the approved blueprint, not a place to infer one. Keep `approval.state` pending and do not run the helper while any target, authority, frozen boundary, or rendered content remains unresolved.

### 3. Apply within authority

1. Adapt only the role templates the blueprint requires.
2. Seed facts checked against artifacts or explicit decisions; mark unknowns and provisional items.
3. Safely merge startup, task-routing, and closure rules into the actual discoverable entry. Never replace an existing `AGENTS.md` or equivalent wholesale.
4. Link the entry to long-term memory, status, and task-specific authorities.
5. Populate the capability route table with installed Skills only. Combine each capability's current trigger description with project-specific authorities; never hard-code unavailable sibling Skills into an independently installed template.
6. Create project or deliverable directories only after their ownership and lifecycle are clear.
7. For a deterministic bootstrap, record the exact approving role, decision ID, and time-zone-aware approval time only after the full create-and-merge plan is authorized and the frozen inventory is complete. Validate every content hash, then run the helper without `--apply` and review its JSON change manifest before applying the unchanged manifest. The agent still owns all semantic design; the helper only executes the declared create-and-managed-block operations.
8. Stop on any manifest, path, frozen-boundary, existing-content, or managed-block conflict. Re-inventory and obtain renewed approval if the targets or rendered content change; never weaken the manifest or edit around the conflict.
9. Do not move, delete, overwrite, unfreeze, publish, or install background automation without the required separate authorization. The bootstrap helper has no operation for any of them.

Follow [bootstrap-manifest-contract.md](bootstrap-manifest-contract.md) for the exact schema, fixed markers, dry-run/apply commands, and stop conditions.

### 4. Verify drift and resumption

1. If the deterministic helper was used, compare observed post-write hashes with planned hashes, then run the same apply command again and confirm it reports only existing or unchanged objects while the workspace remains byte-identical.
2. Run the read-only audit script and review its findings semantically.
3. Reconcile links, authority conflicts, status claims, and frozen identities against physical artifacts.
4. Run a fresh-session task with only the root entry and a user-like request.
5. Run a no-change closure and confirm memory-file hashes remain unchanged.
6. Record remaining risks and the event that should trigger the next review.
7. Start a fresh agent session with representative project tasks and confirm the local entry causes the appropriate installed capabilities to be selected without the user naming them; treat this as behavioral evidence, not a guarantee about every future model build.

When several projects share assets, keep shared authorities once at the common scope and reference them. Keep project-specific state inside the owning project. If an existing unusual layout already provides unambiguous ownership, routing, and lifecycle separation, preserve and map it instead of renaming for aesthetics.

## Migration and Rename Procedure

1. Resolve exact source and destination paths and frozen boundaries.
2. Identify the authoritative copy and duplicates before moving anything.
3. Prefer recoverable, staged changes; do not destructively clean broad directories.
4. Update startup rules, READMEs, memory routes, asset indexes, scripts, dependency graphs, ignore rules, and document links.
5. Search for the old path and stale identifier.
6. Compare file counts and, for authoritative assets, content hashes.
7. Record the migration and any intentional compatibility alias.
8. Re-run the three-hop startup test.

If physical assets and indexes disagree, physical inspection establishes location and content; the repaired index then becomes the routing authority.

## Integrity Audit

Audit at four levels:

### Structural

- expected entry points exist;
- every active status has a parent route;
- every important asset has an owner and authority state;
- topic memories are reachable without being loaded by default;
- history and audits are outside active-status prose.

### Referential

- Markdown and declared file links resolve;
- stable IDs are unique;
- paths use the intended root convention;
- moved or retired assets have no unexplained active references;
- mirrors and derivatives state their upstream authority.

### Semantic

- status matches physical artifacts;
- stable design is internally consistent and explicitly superseded where changed;
- next actions are executable and blockers have clearance conditions;
- missing output is distinguished from a verified zero result;
- duplicated claims do not create competing truths.

### Privacy and Portability

- no secret, credential, personal identifier, private URL, or sensitive record is embedded unnecessarily;
- local absolute paths are isolated from reusable products;
- private assets are excluded from public version control and examples;
- frozen archives remain unchanged;
- public templates contain placeholders, not project facts.

The deterministic audit reports inspectable signals; it does not decide scientific truth, authority ownership, or whether a status statement is factually current. Resolve those against primary artifacts and explicit decisions.

## Public Product Extraction

When generalizing the method for publication:

1. extract the workflow rule, not the incident narrative;
2. replace names, counts, paths, results, and unpublished wording with neutral abstractions;
3. use synthetic examples;
4. document public influences and licenses;
5. validate the clean exported package independently;
6. scan both current files and history before release;
7. publish from a separate clean repository, not from a private working tree.

## Acceptance Evidence

Retain a compact audit record containing:

- inventory scope and date;
- authority map;
- files created or changed;
- conflicts resolved and evidence used;
- link and stale-path results;
- privacy and portability results;
- fresh-session test prompt and observed outcome;
- remaining risks and next review trigger.
