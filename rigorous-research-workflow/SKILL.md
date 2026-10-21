---
name: rigorous-research-workflow
description: "Govern linked research artifacts when lifecycle state, upstream invalidation, frozen baselines, or release decisions must be coordinated across design, evidence, writing, delivery, or public release. Use when a task needs traceable change propagation or multi-artifact transition gates; let specialist skills handle ordinary combinations. Do not use for a single review, draft, document edit, analysis, citation, or routine debugging."
metadata:
  version: "1.0.0"
---

# Rigorous Research Workflow

## Purpose

Coordinate a traceable chain across research stages without duplicating the work of specialist Skills. Preserve one purpose and truth model while evidence, analysis, prose, rich documents, and public packages evolve; propagate changes to every affected artifact and stop invalid downstream state from being treated as current.

## Trigger Gate

Use this Skill only when at least one condition holds:

- an upstream authority, approved requirement, evidence snapshot, result, or purpose change invalidates multiple downstream artifacts;
- exact lifecycle state must be recovered or advanced through gates such as candidate, submitted/frozen, revision, or public release;
- several linked deliverables need one traceable transition, authority map, or release decision.

Two specialist Skills may compose directly without this orchestrator. For example, evidence plus prose or prose plus DOCX engineering is an ordinary specialist handoff unless the request also needs lifecycle state, invalidation propagation, a frozen baseline, or a multi-artifact release gate. For a single review, draft, citation, DOCX cleanup, computation, genomic design, or imputation benchmark, route directly to the matching specialist.

## Route the Task

Classify the request before acting:

- **Design/evidence handoff or interpretation boundaries:** read [research-design-and-evidence.md](references/research-design-and-evidence.md).
- **Evidence-to-content or cross-surface writing handoff:** read [scientific-writing-and-revision.md](references/scientific-writing-and-revision.md).
- **Content-to-delivery, submitted baseline, or revision-round handoff:** read [review-and-delivery.md](references/review-and-delivery.md).
- **Reusable methods, public examples, skill packaging, or release preparation:** read [public-release-and-privacy.md](references/public-release-and-privacy.md).
- **Cross-session workspace continuity, memory routing, or indexed handoff:** compose with `manage-workspace-memory`; let that skill own the memory architecture and lifecycle.

Read every interface that applies. Use specialized search, citation, statistics, visualization, Word, PDF, or domain skills for operations this Skill does not implement.

Prefer specialized Skills for execution and ordinary adjacent handoffs. The four members of Research Skills Suite cover general scientific work. Genomics, document engineering, and workspace-memory Skills are optional companions from separate groups; their examples do not make those groups mandatory or genomic study a default. Use an available equivalent or a bounded direct implementation when a named companion is absent. Use this Skill as the governing layer only when the task satisfies the Trigger Gate above.

## Compose with Specialized Skills

User instructions, project rules, reporting standards, and journal requirements override default preferences from this or any adjacent skill.

| Responsibility | Primary owner |
| --- | --- |
| Stage selection, cross-stage state, invalidation propagation, transition gates, and release decision | This skill |
| Traceable search, screening, primary-full-text verification, and synthesis | `evidence-traceable-literature-review` |
| Scientific document drafting, translation, comment-driven language revision, and prose generation | `scientific-writing-and-revision` |
| Word, Markdown, PDF, review-markup, OpenXML, and rendered-delivery engineering | `research-document-delivery` |
| Reproducible local/HPC workflows, provenance, reruns, handoffs, and public-code separation | `reproducible-computational-research` |
| Reference-aware, species-aware, and complex-genome study design | `genomics-study-design` |
| Genotype-imputation workflow contracts, metrics, leakage controls, and downstream benchmarking | `genotype-imputation-benchmarking` |
| Cross-session rules, status, design, asset, topic-memory routing, and recoverable handoff | `manage-workspace-memory` |
| Broad external literature retrieval when current search is needed | `literature-review`, `research-lookup`, or an equivalent search skill |
| Citation metadata, DOI, and bibliography validation | `citation-management` or an equivalent citation skill |
| Statistical analysis and publication figures | Appropriate statistics, analysis, and visualization skills |
| Binary document editing and authoritative rendering | Appropriate Word, PDF, or office-document skills |
| Platform-specific skill scaffolding and schema validation | The current official `skill-creator` |

## Establish the Contract

Before substantial work, identify:

1. The requested mode: answer, diagnose, revise, build, audit, or release.
2. The audience and document type.
3. The authoritative inputs and the artifact that is the current source of truth.
4. The allowed scope of change, privacy boundary, and publication boundary.
5. The acceptance checks, including any checks that require external software or human review.
6. The initial lifecycle state and which downstream artifacts are currently valid, stale, missing, or frozen.

If a missing choice would materially change the scientific conclusion, study design, or external state, stop and ask. Otherwise, state a conservative assumption and continue.

## Lifecycle State Machine

Use the states as gates, not as a forced linear project plan:

| State | Minimum meaning | Normal specialist owner |
| --- | --- | --- |
| `scoped` | purpose, scope, authorities, boundaries, outputs, and acceptance checks are explicit | design/domain Skill |
| `evidence-ready` | required evidence or analysis is verified, traceable, and bounded; material gaps are visible | evidence, analysis, or domain Skill |
| `content-ready` | prose, tables, figures, captions, and summaries implement one purpose and evidence snapshot | `scientific-writing-and-revision` plus relevant specialists |
| `delivery-candidate` | intended files are synchronized, structurally checked, and tied to current content | `research-document-delivery` |
| `submitted/frozen` | exact circulated artifacts and validation records are immutable by identity | `research-document-delivery` plus `manage-workspace-memory` |
| `revision-round` | new feedback or evidence is linked to a frozen or prior baseline and has an explicit invalidation set | affected specialists |
| `public-release` | generalized assets pass privacy, provenance, license, packaging, and clean-history gates | release and platform specialists |

A task may begin midway, return to an earlier state, or omit irrelevant states. Never advance merely because a file exists. Record the evidence that satisfies the gate and every validation that remains unavailable.

Use [WORKFLOW_STATE.json.template](assets/WORKFLOW_STATE.json.template) when the lifecycle must persist or be machine-checked. Validate it with:

```text
python scripts/validate_workflow_state.py workflow-state.json
```

Schema 2.0 represents every downstream invalidation as a structured record bound to a current authority or required-output ID. An open invalidation forces `revision-round`; advancement requires every critical invalidation to resolve to a replacement identity, all declared rechecks, and inspectable evidence. Noncritical waivers require an explicit decision and residual risk. Read [workflow-state-contract.md](references/workflow-state-contract.md) before creating, resolving, waiving, or migrating persisted invalidations. The validator reports structural closure only; it cannot decide that a repair is scientifically adequate.

## Transition Record

For every consequential transition, retain:

- transition ID, prior state, new state, date, and decision owner;
- purpose-contract and approved-design identities;
- authoritative evidence or analysis snapshot;
- content snapshot and affected reader-facing surfaces;
- delivery artifact and validation identity when applicable;
- privacy/publication boundary;
- unresolved blockers, invalidated downstream artifacts, and next action.

Reference invalidations by their stable `invalidation_id` in the transition record. Do not advance a stale artifact merely by deleting its invalidation; resolve it to current evidence and required rechecks, or retain a permitted noncritical waiver.

Hashes are appropriate for exact files; stable IDs and versions may identify logical designs or evidence snapshots. Do not invent a hash for an object that has not been materialized.

## Run the Orchestration

### 1. Recover and verify current state

Inspect applicable rules, status, design, evidence, content, delivery, and release records. Reconcile their claims with physical artifacts. If the work spans sessions, compose with `manage-workspace-memory` and let it own persistence and startup routing.

### 2. Freeze purpose and truth boundaries

Record the question, intended contribution, unit and scale, required outputs, claims by epistemic status, approved requirements, disallowed substitutes, and authority for material facts. Do not draft quantitative conclusions before their data or cited evidence is verified.

### 3. Plan stages and delegate

Choose only the stages needed to reach the requested outcome. Assign each operation to its primary specialist Skill and define its input and handoff contract. This Skill owns coordination; it does not reimplement literature search, prose revision, OpenXML editing, statistical analysis, or domain methodology.

### 4. Propagate durable changes

When an upstream authority changes, mark dependent state invalid before revising it:

| Durable event | Recheck or invalidate |
| --- | --- |
| question, scope, estimand, input contract, or approved method changes | evidence/analysis plan, claims, outline, tables, conclusions, and delivery |
| evidence is added, removed, contradicted, or changes role | evidence ledger, citations, prose, tables, figures, abstract/conclusion, short summary, and source package |
| analysis data, code, metric, denominator, or result changes | result claims, uncertainty, tables, figures, interpretation, and every derived file |
| content structure or wording changes materially | claim/citation mapping, cross-format parity, package validation, render, and delivery hash |
| delivery file or package membership changes | package audit, authoritative render, validation record, and release identity |
| submission or formal circulation occurs | freeze exact artifacts; route later work to `revision-round` |
| private practice becomes a reusable product | remove local facts; rerun privacy, provenance, license, metadata, installation, and clean-export gates |

Do not repair only the surface where a defect was reported. Trace the dependency to every affected artifact, but do not touch unrelated outputs.

### 5. Validate the transition

Require the specialist completion gate for each stage plus cross-artifact consistency, purpose stability, evidence-status parity, privacy boundaries, and current-identity checks. A historical render, hash, search snapshot, or validation does not validate a changed artifact.

### 6. Persist and hand off

Report outcome, authoritative artifacts, completed and unavailable checks, invalidations, blockers, current state, and one executable next action. Persist only durable state through `manage-workspace-memory`; keep project facts out of reusable Skill packages.

## Cross-Stage Invariants

- Data and primary evidence precede narrative; evidence strength governs wording.
- Purpose, unit, scale, definitions, and epistemic status remain consistent across long and short forms.
- Every material change has one authority and an explicit downstream invalidation set.
- Held-out evaluation information remains isolated from development decisions.
- Exact delivery and submission claims are bound to the current artifact identity.
- Private or unpublished project facts do not enter public products, examples, logs, or external services without authorization and review.
- Submitted baselines remain frozen; later feedback starts a linked revision unless the user explicitly reopens them.
- Missing or unrun validation is reported, never silently inherited from an earlier artifact.

## Completion Standard

A governed transition is complete only when the requested artifacts exist, every required participating-specialist gate has passed for the current identities, downstream state reflects the final authorities, the lifecycle transition is evidence-backed, privacy and frozen boundaries hold, and the handoff identifies the current state and next action. An unavailable required check keeps the relevant artifact or transition in a candidate or blocked state; it may be handed off with the limitation, but it is not a passed delivery or public-release gate. Only an explicitly authorized waiver of a non-required check may close without a pass, and the waiver and residual risk must be recorded.
