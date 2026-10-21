---
name: evidence-traceable-literature-review
description: "Build and audit evidence-traceable literature reviews and source packages. Use when a task needs multi-source discovery plus screening, primary-full-text verification, claim-to-source matrices, contrary evidence, novelty or citation-delta audits, bibliography changes, or review synthesis. Compose with search, citation, database, and PDF skills. Do not use for one DOI, a routine fact, or prose-only editing."
metadata:
  version: "1.0.1"
---

# Evidence-Traceable Literature Review

## Purpose

Turn a research question into a reproducible search, an inspectable evidence trail, and a synthesis whose material claims can be traced to primary sources. Treat discovery, verification, synthesis, and delivery as separate stages.

## Route Supporting Skills

Named companions outside Research Skills Suite are optional, separately installed examples. Use the actual host's available search, document or domain capability; a missing named companion does not require installing its entire group. Keep the evidence and handoff contract intact when choosing an equivalent.

Use this skill as the evidence-closure layer. Compose it with:

- search or database skills for current discovery;
- citation-management skills for DOI and bibliographic metadata;
- PDF or document skills for full-text extraction and visual checks;
- `scientific-writing-and-revision` for argument construction or reader-facing prose;
- `research-document-delivery` when the bibliography, evidence matrix, or full-text package must be synchronized with Word, Markdown, or PDF deliverables;
- domain skills for specialist terminology, methods, and biological interpretation.

If a specialized tool is unavailable, preserve the same query, screening, and evidence records with the best accessible source. Never let a search snippet substitute for primary evidence.

## Establish the Review Contract

Before searching, record:

1. **Decision or question:** what the review must help the reader decide or understand.
2. **Review stance:** evidence map, method comparison, novelty audit, compliance defense, causal or mechanistic appraisal, or narrative synthesis.
3. **Scope:** population or domain, intervention or method, comparator, outcome, years, languages, publication types, and exclusions.
4. **Evidence threshold:** which claims require original full text, supplementary material, authoritative databases, or independent corroboration.
5. **Deliverables:** search log, screening ledger, evidence matrix, prose, bibliography, full-text package, or gaps list.

If the question uses words such as “first,” “best,” “all,” “none,” “standard,” or “recommended,” raise the verification burden explicitly.

## Resume Before Restarting

When continuing an existing review, inspect its search ledger, last completed source and pagination/export cursor, screening decisions, retrieved full texts, evidence matrix, citation-delta record, and package manifest before issuing a new query. Resume from the last verified boundary and reuse validated source identities. Do not restart merely because the prior work used different filenames or tools.

Restart or broaden a search only when the question, scope, date boundary, source coverage, or prior audit shows that existing discovery is inadequate. Record what was reused, invalidated, and newly searched so repeated sessions remain idempotent.

## Run the Workflow

### 1. Decompose the Question

Translate the request into concepts, synonyms, historical terms, tool names, spelling variants, abbreviations, and negative or competing hypotheses. Separate discovery queries from verification queries.

Read [search-and-screening.md](references/search-and-screening.md) when designing or documenting the search.

### 2. Search Broadly, Then Track Precisely

Use multiple sources when one database cannot cover the field. Save the exact query, source, date, filters, result count, and pagination or export boundary. Deduplicate by stable identifiers and normalized bibliographic fields; never infer that similar titles are duplicates without checking versions.

### 3. Screen with Explicit Reasons

Apply inclusion and exclusion criteria consistently. Retain a record of excluded near-matches and why they were excluded. Preserve negative and contrary evidence rather than silently dropping it because it complicates the narrative.

### 4. Retrieve the Strongest Available Source

For consequential claims, prefer the original article and its supplementary files. Abstracts, reviews, repository pages, database records, and search snippets are discovery aids unless the claim is limited to metadata they directly establish.

Verify that the file is the intended article, version, year, title, and evidence role. Distinguish preprints, conference abstracts, perspectives, corrections, protocols, and final peer-reviewed reports.

### 5. Build a Claim-Level Evidence Matrix

For each material source, capture the exact contribution, design, sample or dataset, metric definition, result, limitation, and intended use in the review. Link important claims to page, section, table, figure, or supplementary locator.

Read [claim-evidence-audit.md](references/claim-evidence-audit.md) for verification rules and the evidence-ledger schema.

Use the optional machine-readable templates in `assets/` for a durable bundle:

- `search-ledger.tsv` for reproducible queries and cursors;
- `screening-ledger.tsv` for inclusion decisions;
- `evidence-matrix.tsv` for claim-to-source roles and locators;
- `source-manifest.tsv` for delivered full-text identities.

Read [review-bundle-schema.md](references/review-bundle-schema.md) before creating or extending the bundle; it defines the tables, controlled values, path rules, and validator exit contract. The files under `assets/` are header-only output templates, not agent instructions.

Validate their structural closure without changing them:

```text
python scripts/validate_review_bundle.py --bundle review-bundle --format text
```

The validator can find missing IDs, files, hashes, and relations. It cannot decide whether a paper scientifically supports a claim; audit that judgment against the primary full text.

### 6. Synthesize by Scientific Problem

Group evidence by concept, method role, comparison, disagreement, boundary, or temporal development. Do not write one paragraph per paper unless the document is explicitly an annotated bibliography.

Use the chain:

`problem -> concept or method development -> representative evidence -> disagreement or limitation -> bounded synthesis -> implication`

State when studies are not directly comparable because populations, truth sets, filters, metrics, software versions, or denominators differ.

### 7. Manage Citations and Full Text as Deliverables

For numbered styles, assign numbers by first appearance only after the narrative order is stable. After every structural revision, recheck citation order, reference resolution, metadata, and local file mapping. Use a collision-safe two-pass remapping when many numbers change.

After the last pruning or renumbering pass, inspect the actual handoff directory: compare the current bibliography against the validated mapping, recompute file hashes, parse every delivered full text, and exclude placeholders, temporary files, and background sources from the reader-facing package.

Read [synthesis-and-delivery.md](references/synthesis-and-delivery.md) for synthesis structure, reference renumbering, and full-text package checks.
Read [citation-delta-audit.md](references/citation-delta-audit.md) whenever a passage or source is deleted, merged, replaced, newly added, or moved. Audit source roles and claim support before treating the revised bibliography as complete.

### 8. Audit Before Handoff

Confirm:

- every consequential claim has an appropriate source;
- every citation supports the adjacent statement at the stated scope;
- contradictory or absent evidence is visible;
- search coverage and limits are disclosed;
- every reference resolves to correct metadata and, when required, a verified full text;
- prose, bibliography, evidence matrix, and full-text package agree.
- the before/after citation ledger has no orphan sources, unsupported additions, role mismatches, or unjustified citation inflation.

## Evidence Handoff Contract

For a downstream writing, analysis, delivery, or future-session task, report:

- review question, scope, search boundary, and last verified cursor;
- evidence-snapshot ID and the exact ledgers it covers;
- each material claim's epistemic status, evidence role, source ID, and primary locator;
- verified source identity and full-text hash where an exact local file is required;
- contradictory evidence, unavailable full text, unresolved metadata, and coverage limits;
- content surfaces invalidated by the evidence delta: body, table, figure, abstract, conclusion, short summary, bibliography, or package.

If this handoff persists across sessions, compose with `manage-workspace-memory`; record safe pointers and state rather than copying full-text or sensitive content into startup memory.

## Non-Negotiable Rules

- Declare the review stance before interpreting the evidence.
- Return important scientific assertions to the original full text.
- Search exact terms and plausible synonyms before claiming absence.
- Treat “first” or “earliest” as a citation-chain question, not a title-search result.
- Check the direction and order of magnitude of recommended values.
- Record evidence against the preferred conclusion.
- Never turn a database cutoff, language limit, or unavailable full text into a universal absence claim.
- Do not use citation quantity as a substitute for claim-level support.
- Do not retain a reference merely because its number survived editing, and do not add a source merely to decorate a new sentence; both decisions require an explicit evidence role.

## Stop or Ask When

Pause for direction when alternative scope choices would change the conclusion, the required source is inaccessible and no equivalent evidence exists, the user requests an exhaustive claim without an adequate search boundary, or the evidence package contains conflicting versions that cannot be reconciled safely.

## Completion Standard

A review is complete when the search and screening are reproducible, any prior review was resumed or invalidated explicitly, material claims are traceable to verified sources, disagreements and limits are represented, the synthesis answers the stated question, citations and full-text artifacts are internally consistent, and downstream consumers receive a versioned evidence handoff with unresolved gaps.
