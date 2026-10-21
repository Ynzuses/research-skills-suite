# Synthesis and Delivery

## Build the Narrative

Organize by the reader's problem, not the order in which papers were found. A strong structure is:

1. define the problem and scope;
2. explain the relevant concept or metric;
3. show how evidence or methods developed;
4. compare representative findings on commensurate terms;
5. expose disagreements, missing dimensions, and limits;
6. state the bounded synthesis;
7. explain the implication for the present decision or study.

Each paragraph should make one central judgment and show why the cited evidence supports it. Do not end with generic claims of importance when a specific contribution or limitation can be named.

## Comparison Matrix

For method or benchmark reviews, include fields that prevent false equivalence:

- scientific task and information source;
- population, organism, cohort, or dataset;
- sample or panel size;
- truth definition;
- software and version;
- filtering and evaluation space;
- metric definition and aggregation;
- reported performance;
- unavailable or selectively reported cases;
- limitation and transfer boundary.

Never compare identical metric labels until their definitions, filters, and denominators are confirmed.

## Numbered Citation Workflow

When citations follow order of first appearance:

1. stabilize the section and paragraph order;
2. extract citation groups in reading order;
3. compute the ideal old-to-new mapping;
4. replace old numbers with collision-safe temporary placeholders;
5. replace placeholders with final numbers;
6. reorder the reference list;
7. verify every citation resolves and every reference is used;
8. verify Word, Markdown, bibliography, and full-text filenames agree.

Direct sequential substitutions can corrupt numbers when mappings overlap, such as 1→2 and 2→3.

## Full-Text Package

For a deliverable source folder:

- keep exactly one intended file per cited reference unless multiple versions are deliberately documented;
- use continuous, deterministic numbering when the package follows numbered citations;
- verify identity and content hash before and after rename or move operations;
- after the final bibliography revision, compare current reference text and order against the retained source mapping;
- parse every delivered full text and require a nonzero page or equivalent content count;
- keep excluded or background files in a clearly separate, recoverable audit location;
- exclude placeholders, editor locks, staging files, and non-delivery formats from the reader-facing directory;
- record hard links or shared truth files so they are not mistaken for independent copies;
- disclose unavailable full text rather than inserting an unverified substitute.

## Delivery Checklist

- Search log and screening boundary are present.
- Evidence ledger resolves every material claim.
- Synthesis represents conflicting and null evidence.
- Citation order and metadata pass validation.
- Full-text files map one-to-one to the intended references.
- Every delivered full text is structurally readable, hash-bound to the validated identity, and the package contains no temporary or placeholder files.
- Partial repository or database audits are labeled partial.
- Reader-facing prose excludes internal search mechanics unless the document type requires them.
- When content is deleted or added, attach a [citation-delta-audit.md](citation-delta-audit.md) ledger to the review record and re-audit the conclusion and any short summary whose evidence scope changed.
