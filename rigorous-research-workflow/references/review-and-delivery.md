# Content-to-Delivery Handoff

This is the orchestration interface between approved content and final research files. It is not an OpenXML or rendering manual. Delegate DOCX, Markdown/PDF synchronization, comments, tracked changes, package cleanup, rendering, hashes, and submitted baselines to `research-document-delivery`.

## Required Inputs

- content snapshot and purpose-contract identity;
- authoritative direction among Markdown, Word, PDF, or another source;
- baseline, reviewed original, candidate, and intended final roles;
- accepted feedback decisions and changed surfaces;
- required citations, equations, figures, tables, numbering, styles, and application-specific constraints;
- target deliverable set and prohibited audit, lock, staging, or private members;
- validation and submission requirements.

If comments require scientific judgment or prose repair, call `scientific-writing-and-revision`. If bibliography or claim support changed, call `evidence-traceable-literature-review` before freezing delivery.

## Specialist Output Contract

The delivery stage returns:

- exact candidate or final artifact identities and package membership;
- authority and synchronization direction;
- baseline and backup identities where needed;
- content-parity, package-structure, markup, citation/equation/table/figure, and render results;
- checks not run or not authoritative;
- submitted or frozen identity, or next revision identity;
- every downstream release record invalidated by a file or package change.

## Cross-Stage Gate

A file becomes a `delivery-candidate` only when it implements the current content snapshot, applicable specialist checks pass, and validation is bound to that exact identity. A static package inspection does not prove visual layout; an older render does not validate a changed hash.

At formal circulation, transition to `submitted/frozen` and preserve the exact file, companion artifacts, validation record, and package membership. New evidence or feedback creates a linked `revision-round`; it never silently mutates the frozen baseline or inherits the old validation.

Any content, file, relationship, package-member, or metadata change invalidates the affected hash-bound package and render records. Re-run only the applicable gates, but never claim an invalidated result as current.
