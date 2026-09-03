# Validation and Release

## Package Checks

- ZIP container opens and all expected parts parse.
- Content types and relationship targets resolve.
- Document, styles, numbering, settings, themes, fonts, media, headers, footers, footnotes, and endnotes are present when expected.
- Comments, replies, people/authors, presence metadata, anchors, and revision nodes match the requested clean or reviewed state; relationships and content-type registrations contain no residue or dangling targets.
- Equation, hyperlink, field, bookmark, drawing, and media counts remain plausible.
- Automatic numbering definitions and section properties remain valid.
- Distinct character-format roles touched by editing, including citation superscripts and language-specific punctuation fonts, retain their expected run-property signatures.
- Validate formula and citation runs by semantic role and text, not only by aggregate superscript/subscript counts. A citation split can legitimately change the number of superscript runs, while a variable can retain its vertical position yet lose its math font or italic property. For every rebuilt formula, check the expected variable text, math font, italic state, and subscript/superscript role together.

## Content Checks

- Normalized Word and Markdown blocks agree in the intended direction.
- Headings and section assignments are correct.
- Table cells, captions, formulas, citations, and references are included in comparison.
- Numbers, signs, units, versions, conditions, and terminology match the authoritative sources.
- Figure and table references follow physical first appearance.

## Render Checks

Open the final document in the authoritative application and inspect:

- actual page count and section breaks;
- heading isolation and orphaned captions;
- paragraph, table-row, and formula wrapping;
- table splitting, widths, merged cells, and repeating headers;
- figure placement, cropping, resolution, and caption association;
- citation superscripts, variables, superscripts, subscripts, and symbol fonts;
- headers, footers, margins, page numbers, hyperlinks, and cross-references.

If a PDF is the delivery format or rendering proxy, generate it from the final document and bind the PDF to the source hash. Render only the pages needed for visual inspection, but never use pages rendered from an older source.

## Delivery Directory Checks

- Enumerate the actual handoff directory, including hidden files.
- Keep only intended reader-facing documents and explicitly requested source packages. Exclude editor locks such as `~$...`, staging candidates, conversion by-products, placeholders such as `.gitkeep`, and internal audit files.
- Before removing an editor lock, confirm the authoritative application is not running and the file is clearly ephemeral; otherwise preserve it and ask.
- For a numbered source package, require one parseable file per reference, continuous deterministic numbering, expected hashes, and no unrelated formats.
- A prior audit may be reused only when the current artifact hashes equal the recorded hashes, all recorded checks are true, and the failure list is empty. Re-audit any surface changed after that record, including directory membership.
- Treat status panels, README files, asset indexes, and audit pointers as post-build metadata. After editing them, rebind the final Word/Markdown hashes and rerun the hash-bound release check; a previously passing audit does not automatically validate the post-metadata handoff.
- Once a document has been submitted or formally circulated, treat its recorded hash as a frozen baseline. A later revision must be a new artifact with its own backup, synchronization record, and validation; never report a new copy as validated by the submitted copy's render or audit.

## Citation and Numbering Checks

- Extract citation groups in reading order.
- Confirm monotonic first appearance according to the target style.
- Confirm reference-list numbering is continuous and displayed correctly.
- Confirm all figures and tables are numbered in appearance order.
- Confirm text references, captions, physical objects, filenames, and change records agree.

## Delivery Record

Record:

- authoritative source and output paths;
- baseline, backup, final Word, synchronized Markdown, and PDF hashes where applicable;
- accepted, rejected, and unresolved comment counts;
- whether tracked changes and comments were removed;
- content, package, cross-format, citation, and render results;
- the exact checks not run and why.
- the final delivery-directory membership and any excluded temporary or audit artifacts.

Use `DELIVERY_RECORD` schema 2.0. Declare `required_gates` on every artifact so the delivery-member list, gate profile, validation records, current artifact hashes, and evidence hashes form a closed set. Each artifact, gate declaration, validation, evidence object, not-applicable decision, and the root record carries an `extensions` object for namespaced future fields. Schema 1.0 prose evidence is not accepted as final proof: migrate it to structured local evidence and rerun the affected check. Unknown versions fail closed until deliberately migrated.

## Gate Semantics

Define the applicable validation profile before release. For each check, record whether it is required, its current state, the artifact identity it validates, and its evidence locator.

- `passed`: current evidence satisfies the check for the recorded artifact hash;
- `failed`: the candidate cannot advance;
- `unavailable`: the check was required or desired but could not be run; record the cause and retry condition;
- `not-applicable`: the delivery contract explains why the check does not apply;
- a non-required check may be omitted; if an already-declared gate is found genuinely inapplicable, record its specific reason, authorizer, and timezone-qualified decision timestamp.

`final`, `submitted`, `frozen`, and public-release states require a non-empty applicable validation profile and a closed result for every required check, all bound to current artifact identities. Passed results use a local ordinary evidence file identified by relative path and SHA-256. Human rendering or inspection is preserved in that file; an unstructured assertion, external locator, nonexistent file, symlink, or stale hash cannot support release. Required rendered and delivery-package gates cannot be replaced by `not-applicable`. An unavailable required check keeps the item at candidate or blocked state. A limited handoff is allowed when useful, but its label and next action must preserve that limitation.

The verifier deliberately emits `STRUCTURAL PASS`: it verifies identity and closure mechanics, not the truth or adequacy of the evidence file's contents. Completion still requires the Skill's substantive review.

Do not call an artifact “fully validated” when authoritative rendering failed, timed out, was unavailable, was waived despite being required, or used a different hash.
