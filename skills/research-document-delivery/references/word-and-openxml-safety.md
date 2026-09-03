# Word and OpenXML Safety

## Contents

- [Baseline Inventory](#baseline-inventory)
- [Traversal](#traversal)
- [Paragraph and Run Safety](#paragraph-and-run-safety)
- [Equations and Fields](#equations-and-fields)
- [Comments and Revisions](#comments-and-revisions)
- [Numbering, Tables, and Media](#numbering-tables-and-media)

## Baseline Inventory

Before editing, record the file hash and counts of document parts, paragraphs, tables, styles, numbering definitions, sections, equations, hyperlinks, media, comments, replies, comment anchors, and revision nodes. Inspect macros or embedded objects when present.

Keep the reviewed original in a separate audit location. A copy inside the same overwrite sequence is not an independent backup.

## Traversal

High-level libraries often expose body paragraphs and tables separately. They may omit paragraphs inside table cells from `document.paragraphs` and may not preserve the true body order of paragraphs and tables. Traverse the document XML in body order when sequence matters, and recurse into table cells for comments, citations, references, and text comparison.

Identify the reference-section boundary from a genuine heading style and context. A table column labeled “References” or a caption containing the word is not the section heading.

## Paragraph and Run Safety

Paragraph text is distributed across runs with styles, superscripts, fields, hyperlinks, bookmarks, proofing marks, equations, and drawings. Before replacing a paragraph, inspect its child sequence.

Prefer:

- minimal substitutions within existing text runs;
- preserving run properties when replacing text;
- cloning a known-good neighboring structure only when semantics match;
- comparing child element types before and after.

Before rebuilding even a plain paragraph, classify its run-property signatures and the tokens that require them. Preserve or explicitly recreate citation superscripts, variables, emphasis, language-specific punctuation fonts, hyperlinks, and any other distinct character formatting. Do not infer the entire paragraph's character style from its first visible run.

Avoid clearing all runs and adding one plain run. That destroys semantic formatting even when the visible text appears correct.

## Equations and Fields

OMML equations are not plain text. A paragraph containing `m:oMath`, `m:oMathPara`, field characters, instruction text, drawings, hyperlinks, or bookmarks must not be reconstructed by a text-only API.

For a targeted wording change in such a paragraph:

1. locate the specific `w:t` run outside protected elements;
2. modify only that node;
3. preserve surrounding child order;
4. compare equation and field node counts and serialized structure;
5. render the result.

## Comments and Revisions

A comment can involve the comments part, people/authors or replies parts, presence metadata, comment range start/end anchors, reference markers, package relationships, and content-type registrations. A clean copy should contain none of the resolved structures required by the target Word version. Filename searches for `comment` are insufficient because `word/people.xml` and `/relationships/people` may remain after visible comments disappear.

Tracked changes may wrap inserted or deleted text in revision elements. Decide whether each change is accepted or rejected before cleanup. Deleting all revision elements can delete both visible and hidden content.

After cleanup, verify zero remaining comment, reply, people/author, and presence parts; zero anchors, references, revision nodes, related relationships, and content-type registrations; and no dangling targets, while confirming the expected text remains.

## Numbering, Tables, and Media

Preserve list paragraph properties, abstract numbering definitions, numbering instances, and displayed continuity. A visually typed number is not equivalent to automatic numbering.

For tables, protect merged cells, widths, row properties, repeating headers, captions, and the order of cell paragraphs. For figures, protect relationship IDs, anchors, extents, alternative text, captions, and source media. Changing a displayed caption number also requires checking all cross-references and the physical order of the object.
