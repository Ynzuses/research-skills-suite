# Architecture and Authority

## Design Goal

A workspace memory system should minimize recovery cost while preserving evidential authority. It is a navigable control plane over the workspace, not a second copy of the workspace and not a substitute for primary data, code, documents, or version history.

## Layer Model

Assign one responsibility to each layer. Existing workspaces may use different names; map by function before adding files.

| Layer | Required content | Normal update trigger | Normal read trigger |
| --- | --- | --- | --- |
| Rules | collaboration constraints, permissions, privacy, startup and closure requirements | policy or boundary change | every new session |
| Long-term index | stable rules, active-area routes, memory topology, authoritative entry points | route or durable cross-project lesson changes | every new session |
| Status | objective, verified state, next action, blockers, recent authoritative outputs | material progress or blocker changes | when entering that scope |
| Stable design | scope, definitions, inputs, contracts, locked and provisional decisions | approved design change | when the task depends on design |
| Asset index | stable ID, role, authority, location, source, status, verification | asset creation, move, replacement, or retirement | when locating or choosing an artifact |
| Topic memory | bounded domain knowledge, methods, unresolved questions, topic routes | durable topic learning | only for matching tasks |
| Dependency graph | stage and artifact dependencies, upstream and downstream effects | topology changes | planning, impact analysis, recovery |
| History | dated decisions, changes, evidence, supersession | consequential closure | audit or reconstruction |
| Audit archive | detailed logs, comparisons, snapshots, closed evidence | closure or investigation | only when verification requires detail |

## Three-Hop Progressive Read

The default navigation contract is:

```text
rules + long-term index
          |
          v
    current status
          |
          v
stable design / asset index / topic memory / primary artifact
```

The three hops are logical, not necessarily three files. A small workspace may combine long-term index and status, while a large workspace may have one status panel per project. Preserve the responsibilities even if files are combined.

The startup entry must not link indiscriminately to everything. It should route by active scope and task type. Topic files should link back to their parent status or index so navigation is reversible.

## Typed Authority Map

Avoid a single claim such as “the newest file always wins.” Authority depends on the question.

| Question | Primary authority | Corroboration | Repair when inconsistent |
| --- | --- | --- | --- |
| Does the artifact exist and what does it contain? | physical artifact or primary system | hash, render, query, execution log | repair status and index after inspection |
| What design is currently approved? | stable design or explicit decision record | current status, history | record supersession; do not edit history away |
| What should happen next? | current status | artifact state, blockers | replace stale action and timestamp verification |
| Where is the authoritative asset? | verified asset index | filesystem or repository inventory | update all inbound routes after confirming target |
| Why was a decision made? | dated history or decision record | commit, audit evidence | add missing evidence; do not turn history into status |
| What may be read, changed, or published? | most specific current rule | licenses, privacy register | stop if authority is missing |

If two artifacts claim the same role, designate one as authoritative. Mark the other as a mirror, derivative, delivery copy, or historical snapshot, and state the synchronization direction.

## Identity and Links

- Give important assets stable IDs independent of filenames.
- Prefer paths relative to a shared workspace root. Record external roots symbolically when a relative path is impossible.
- Store both human meaning and machine-resolvable location.
- Link to the authority, not to a convenient duplicate.
- Record `supersedes`, `derived from`, `mirrors`, or `depends on` explicitly.
- A rename is incomplete until inbound links, scripts, rules, indexes, and documentation have been checked.

Absolute paths may be necessary for local execution, but they reduce portability and must not enter public templates or reusable products.

## Infer a Workspace Profile

Infer structure from the work rather than from a favorite directory tree. Record the reasoning in a workspace blueprint.

| Project characteristic | Structural consequence |
| --- | --- |
| one short-lived deliverable and few durable decisions | combine compatible roles; use a lean control plane |
| multiple deliverables with different owners or release cycles | give each owning scope a status and design route |
| two or more projects consume the same authoritative input, code, or method | keep one shared authority at the common scope and reference it |
| sensitive data, public outputs, or different access groups coexist | separate by privacy and publication boundary before convenience |
| local and remote/HPC execution produce derived artifacts | record symbolic roots, provenance, checkpoints, and synchronization direction |
| submitted, published, regulated, or otherwise frozen material exists | isolate it from active revisions and bind its identity |
| large data or generated outputs dominate | keep them outside the memory control plane; index safe metadata and authority only |
| independent teams or repositories own components | federate status and authority; do not create a false single source of truth |

Choose the smallest sufficient profile after this inference:

- **Lean:** discoverable rules, one combined memory/status entry, and a compact asset list. Suitable when one stream and one lifecycle genuinely share readers and authority.
- **Standard:** separate rules, long-term index, status, stable design, asset index, and history. Suitable for durable multi-session work with one primary ownership scope.
- **Federated:** workspace-level rules/index plus per-project or per-deliverable status, design, assets, and topic routes. Suitable for multiple ownership, privacy, repository, or lifecycle boundaries, including related projects sharing authorities.

## Directory Blueprint Principles

1. Partition first by research question, product, deliverable, or authority owner—the unit that can define scope and current state.
2. Organize longitudinal functions such as management, design, data, code, results, documents, and evidence inside that owner only where they are useful.
3. Place genuinely shared authorities once at the nearest common scope. Consumers link to them; they do not clone them into local truth sets.
4. Separate active, frozen, generated, cached, and externally owned material by lifecycle and mutation rights.
5. Keep repository configuration and reusable public products at their natural common scope.
6. Map a coherent existing structure by role. Do not rename it merely to achieve visual uniformity.

Numbered directory schemes are optional local conventions, never universal output. Do not create empty layers merely to match a diagram. Split a file or directory when it has different readers, authority, update cadence, privacy boundary, owner, or lifecycle.

## Relationship to DAG and Version Control

A dependency graph explains structure: what consumes what, which step must precede another, and what a change will affect. History and version control explain time: what changed and what was previously true. Neither answers “what is the verified current next action” as reliably as a status panel.

Keep all three when the project needs them:

- status for resumption;
- DAG for impact and execution order;
- history or version control for reconstruction and accountability.

## Failure Patterns

- Reading every memory file at startup until the system no longer saves context.
- Repeating the same fact in rules, memory, status, README, and topic notes without an authority marker.
- Treating an index entry as proof that its target exists.
- Mixing stable design, transient progress, and dated history into one append-only document.
- Using Git commits as a substitute for a current status panel.
- Using a DAG as a substitute for narrative reasons or decision history.
- Updating memory before checking the artifact, thereby memorializing an assumption.
- Sending private workspace text to an external memory service by default.
