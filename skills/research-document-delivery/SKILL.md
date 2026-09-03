---
name: research-document-delivery
description: "Safely edit, synchronize, clean, render, freeze, and verify Word, Markdown, and PDF research deliverables. Use when file structure, comments or tracked changes, OpenXML, citations, equations, tables, figures, cross-format parity, submitted baselines, or hash-bound final validation matters. Compose with writing and evidence skills for content changes. Do not use for prose-only drafting, citation lookup, generic conversion, or ordinary Markdown editing."
---

# Research Document Delivery

## Purpose

Produce research files that are textually correct, structurally intact, synchronized across formats, clean of resolved review markup when requested, and verified in the application that defines the delivery format.

## Compose with Other Skills

Use `scientific-writing-and-revision` for argument, language, and comment adjudication; use `evidence-traceable-literature-review` when claim support, bibliography roles, or the source package changes. Use the appropriate Word, PDF, or office-document capability for binary editing and rendering. This Skill governs authority, recoverability, synchronization, markup cleanup, and release validation. Compose with `manage-workspace-memory` when delivery identity or a submitted baseline must persist across sessions, and with `rigorous-research-workflow` only for a genuinely cross-stage program.

## Establish Authority and Scope

Before editing, identify:

1. the current content authority;
2. the formatting authority;
3. the reviewed original and clean delivery copy;
4. the direction of Word-Markdown synchronization;
5. whether comments and tracked changes must be retained, resolved, accepted or rejected, or removed;
6. the required rendering application and acceptance checks.

Do not infer authority from filename age alone. Inspect the actual content, comments, revisions, and project state.

If the user has submitted or formally circulated a document, treat that exact file and its hash as an immutable delivery baseline. Do not silently edit it in place. New feedback starts a new revision copy linked to the submitted baseline, with a fresh backup, synchronization record, and validation; reopen the submitted baseline only when the user explicitly authorizes that change.

## Resume an Existing Delivery Round

Before creating another candidate, inspect the current authority/delivery record, verify referenced files and hashes, identify any frozen submitted baseline, and determine which checks remain valid for the current identity. Resume the current revision when its inputs are unchanged; otherwise create a linked revision identity and invalidate only the affected checks.

Use [DELIVERY_RECORD.json.template](assets/DELIVERY_RECORD.json.template) for consequential or multi-round delivery. Verify record-to-file hashes without modifying files:

```text
python scripts/verify_delivery_record.py delivery-record.json
```

The verifier reports `STRUCTURAL PASS`, not delivery completion: it checks the record, local artifact identities, required-gate closure, and evidence-file hashes, but it does not independently decide that the evidence is scientifically or visually adequate. `DELIVERY_RECORD` schema 2.0 makes `required_gates` explicit per artifact. Migrate 1.0 records by declaring that profile, replacing prose evidence with relative-path plus SHA-256 evidence objects, and adding `extensions` objects; unknown schema versions fail closed.

For a DOCX, inventory high-risk package structures read-only before and after editing:

```text
python scripts/audit_docx_package.py document.docx --format text
```

These checks do not replace authoritative application rendering or scientific review.

## Run the Workflow

### 1. Preserve a Recoverable Baseline

Create an independent byte-for-byte backup before changing a rich or irreplaceable document. Verify the backup hash against the editing baseline and never modify the backup. A Git repository does not protect an ignored or untracked binary file.

### 2. Inventory the Package and Markup

Inspect document parts, relationships, content-type declarations, comments, people/authors, replies, comment anchors, tracked revisions, styles, lists, sections, fields, hyperlinks, equations, tables, figures, and embedded objects. Count relevant elements before editing so post-edit loss is detectable.

Read [word-and-openxml-safety.md](references/word-and-openxml-safety.md) before modifying a structured DOCX.

### 3. Adjudicate Review Content

For each comment or revision, record the issue, judgment, reason, local repair, whole-document pattern, and verification. Apply accepted scientific or language changes before removing markup.

Treat reviewer-supplied rewrites and direct tracked edits as proposed wording unless the user explicitly marks them as final. Preserve authoritative factual corrections, but let the scientific-writing adjudication determine the best final prose; record justified departures from the supplied wording.

Do not treat a comment anchor as the default insertion point. When a comment flags an abrupt or undefined term, record whether the final content omits the term, relocates it to its first functional use, or defines it in place. Synchronize the resulting paragraph and any affected table or conclusion, not merely the marked sentence.

If a clean copy is requested, preserve the reviewed baseline, accept or reject tracked changes deliberately, then remove resolved comments, anchors, replies, people/author parts, their relationships and content-type registrations, and tracking metadata. Never delete revision XML nodes as a shortcut because this can discard text.

### 4. Synchronize Deliberately

Choose one path:

- Word content -> Markdown;
- Markdown content -> Word while preserving Word formatting;
- bidirectional reconciliation with explicit conflict decisions.

Read [synchronization.md](references/synchronization.md) for normalized block comparison, table content, headings, and change records.

When the revised outline moves prose or captions across a table or section boundary, move existing document nodes to the intended reading order; do not force new text into the old paragraph positions merely because block counts match. Preserve caption fields by table identity and verify the final flattened reading order including table cells.

### 5. Edit Semantically, Not as Flat Text

Preserve paragraph and character styles, numbering, fields, equations, hyperlinks, drawings, relationships, and section properties. Prefer targeted run-level edits when complex children are present. Do not clear and reconstruct formula-bearing or field-bearing paragraphs.

If a plain paragraph must be rebuilt, inventory every distinct run-property role first and remap it deliberately: citation superscripts, variables, language-specific punctuation fonts, emphasis, hyperlinks, and other character styles. Reusing only the first run's properties is not format preservation. Compare the relevant run-property signatures before and after, in addition to comparing visible text.

### 6. Audit References, Equations, Figures, and Tables

Recheck numbered citations by first appearance, displayed bibliography numbering, superscript and subscript formatting, formula position, figure and table order, captions, cross-references, hyperlinks, and media relationships. Use the actual reference-section heading rather than a similarly named table cell as a boundary.

### 7. Validate in Layers

Declare which layers are required for this deliverable, then run every applicable layer:

1. **Content:** normalized text, tables, references, numbers, and terminology.
2. **Package:** ZIP/OpenXML integrity, parts, relationships, comments, revisions, numbering, fields, equations, and media.
3. **Cross-format:** Word and Markdown block agreement and reference mapping.
4. **Rendered:** page count, pagination, wrapping, headings, captions, figures, tables, formulas, fonts, and links in the authoritative application.
5. **Delivery package:** the handoff directory contains only intended deliverables, with no stale locks, placeholders, temporary candidates, or internal audit artifacts.

Put the applicable gates in each delivery artifact's `required_gates` before validation begins. A final DOCX requires at least content, package, rendered, and delivery-package gates; a final PDF requires at least content, rendered, and delivery-package gates; every other final member requires at least content and delivery-package gates. Draft, candidate, and revision records may retain failed or unavailable gates without claiming finality.

Read [validation-and-release.md](references/validation-and-release.md) for the release checklist and the distinction between a limited handoff and a passed delivery gate.

### 8. Bind Validation to the Delivery File

Record the final file hash after the last save. A render, PDF export, or page count validates only the exact file hash from which it was produced. If the current file cannot be rendered, say so; never reuse a historical page count as current evidence.

For a passed gate, store evidence as a local ordinary file identified by a path relative to the delivery record and its SHA-256. A human inspection may produce that file, but a prose assertion, external locator, missing file, symlink, or stale hash cannot close a final/release gate. Manual or external evidence is allowed only for an explicitly non-file gate or an incomplete draft/candidate record; capture it into an inspectable hash-bound file before final release.

When reusing a prior validation, verify that the current file hashes exactly match the audited hashes, every recorded gate passed, and the audit has no failures. If an authoritative application started by the task hangs or fails, clean up only that task-owned process, confirm no stale lock remains in the delivery package, and record the render failure rather than weakening the gate.

### 9. Freeze a Submitted Baseline

At submission, record the delivery file, synchronized companion files, and final hashes as a frozen baseline. Route later comments to a new round instead of mutating the baseline. The new-round record should identify the baseline, accepted feedback, changed surfaces, and checks that must be rerun; it should not claim that the earlier render or hash validates the new copy.

## Non-Negotiable Rules

- Back up before editing a rich document.
- A text match does not prove character-format, package, or pagination integrity.
- Table-cell paragraphs require explicit traversal; body-only paragraph APIs are incomplete.
- Equal non-table block counts do not prove structural alignment when captions, tables, or sections moved.
- Never flatten a paragraph containing OMML equations, fields, drawings, hyperlinks, or other non-text children without a preservation plan.
- Figure numbering follows first appearance unless the required style states otherwise; synchronize text, captions, filenames, and records.
- Remove comments or review records only after accepted changes are implemented and the reviewed baseline remains recoverable.
- A clean Word package contains no comment, reply, people/author, or review-presence parts and no dangling relationships or content-type registrations for them.
- A clean copy must preserve the intended correction without retaining reviewer dialogue, answer scaffolding, or writing-process instructions in reader-facing prose.
- Validate the final hash, not an earlier intermediate file.
- Do not silently modify a submitted baseline; create and validate a new revision identity.

## Stop or Ask When

Pause if content and format authorities conflict materially, the file contains unsupported objects that cannot be preserved, accepting a tracked change would alter scientific meaning without a decision, or the only review history would be destroyed.

## Completion Standard

Delivery is complete only when the final file opens, requested review markup is handled, scientific content and cross-format text agree, package structure passes inspection, citations and semantic formatting remain valid, the delivery directory is clean, the delivery record resolves to current file hashes, and every required validation—including authoritative rendering when required by the delivery contract—has passed for those hashes. If a required application or check is unavailable, the artifact may be handed off as a clearly limited candidate with the failed or unavailable gate and residual risk recorded; do not label it final, submitted-ready, frozen, fully validated, or release-ready. A genuinely inapplicable gate needs a concrete reason, authorizer, and timezone-qualified decision timestamp; required rendering and delivery-package checks cannot be converted to `not-applicable` in a final/release record. The verifier's structural pass is necessary record evidence, never a substitute for this completion judgment.
