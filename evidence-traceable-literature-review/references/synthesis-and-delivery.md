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

## Reference-Manager Route (Optional)

A reference manager adds a browsable, shareable library and formatted bibliographies. It also adds a second place where source identities live. Decide per task whether the review passes through it, and record the choice with the review contract.

| The task | Route |
| --- | --- |
| must hand over the sources themselves, will be shared with readers who browse or reuse the library, or will be revised over several rounds with a changing bibliography | through the reference manager |
| needs only the result, is short-lived, or cites a handful of sources | ledgers and the full-text folder only |

When the route is used:

- **One authority per fact.** The evidence ledgers and the hash-bound full-text package stay authoritative for which sources support which claims and for the delivered files. The library is a mirror for browsing, sharing and formatting. State the synchronization direction, normally from the verified package into the library.
- **Enter only verified sources.** Add an item after its identity check, by stable identifier where one exists, and attach the same file whose hash the source manifest records. Do not let an automatic metadata lookup or an automatically fetched file replace a verified identity; compare title, authors, year, venue and version after import.
- **Keep keys in the ledger.** Record each item's library key beside its source ID so the two can be reconciled. One collection per review, named for it.
- **Mind what synchronizes.** A library that syncs to a hosted service or a group sends item data, notes and possibly files there. Keep unpublished reasoning, drafting notes and restricted material in the workspace, not in library notes, and check the publisher's terms before placing full texts in a shared library.
- **Generate, then verify.** A bibliography formatted from the library still goes through the citation-order and metadata checks above. A style file encodes a standard's rules imperfectly; compare a sample of each source type with the standard the venue requires.
- **Reconcile before handoff.** The collection's items, the reference list and the full-text package must agree one-to-one; report any item present in one and missing from another.

When the route is not used, nothing is lost: the ledgers and package already satisfy the evidence contract. Do not import sources into a library only because the tool is available.

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
