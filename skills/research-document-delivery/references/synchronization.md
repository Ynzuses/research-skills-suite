# Word-Markdown Synchronization

## Choose Direction

### Word Is the User-Edited Truth

Extract current headings, body paragraphs, table cells, equations in a stable textual representation, citations, and references. Incorporate accepted comments, then update Markdown to match. Preserve a review record separately from the clean Markdown.

### Markdown Is the Content Truth

Map Markdown blocks to existing Word blocks using stable headings and text anchors. Update Word text while preserving styles, lists, semantic runs, tables, equations, relationships, sections, and page setup.

If the revision moves a caption, paragraph, list, or table relative to another block, synchronize the document tree rather than only replacing text in the old node order. Align captions by table identity or number, preserve field-bearing caption nodes, and move existing paragraph/table nodes so their formatting properties travel with them. Equal paragraph counts do not justify positional replacement when section or table boundaries changed.

### Bidirectional Reconciliation

Normalize both formats and classify differences as Word-only, Markdown-only, formatting-only, reordered, or conflicting. Resolve conflicts explicitly; do not silently select the newer timestamp or the file with more text.

## Normalize for Comparison

Use a comparison representation that preserves:

- heading level and title;
- paragraph order;
- list level and item identity;
- table row and cell order;
- formula placeholders or canonical text;
- reference entries and numbering;
- figure and table captions.

Normalize harmless differences such as automatic numbering display, non-breaking spaces, line endings, and equivalent Unicode forms, but retain scientifically meaningful punctuation, symbols, superscripts, subscripts, signs, ranges, and units.

## Structural Reverse Check

A plain text diff can miss a paragraph pasted under the wrong heading. After synchronization, reconstruct the heading tree and assign each paragraph, list, table, and caption to its section. Compare section paths and block order, not only sentence text.

Also flatten the final Word document in reading order, including table-cell paragraphs, and compare it with the Markdown block stream. Verify each caption is adjacent to its intended table and that automatic-number fields remain present; a body-only non-table comparison can pass while prose and tables are interleaved incorrectly.

## Change Record

For consequential revisions, record:

- section path;
- full original paragraph;
- full revised paragraph;
- a unique search anchor in each direction;
- reason for change;
- synchronization result.

Paragraph-level records are more useful than vague page references because pagination changes after editing.

## Citation Synchronization

Compare citation groups in reading order and reference entries separately. Verify:

- every citation resolves;
- every listed reference is cited when required;
- first appearance follows the numbered style;
- Word displayed numbers and Markdown text agree;
- local full-text filenames or bibliography records map to the same identities.

Repeat this check after any paragraph move.
