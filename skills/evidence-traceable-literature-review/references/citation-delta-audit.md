# Citation-Delta Audit

Use this reference after pruning, merging, renumbering, or expanding a review. A bibliography can remain syntactically valid while its evidentiary role has become wrong, so audit the change set rather than only counting references.

## Build a Before/After Ledger

Record one row for each changed claim or source:

| Change | Claim or passage | Old source(s) | New source(s) | Evidence role | Decision |
| --- | --- | --- | --- | --- | --- |
| retained / edited / removed / added | stable passage ID or short quote | citation number or source ID | citation number or source ID | definition, mechanism, comparison, limit, or context | keep, replace, relocate, or flag |

Use stable passage IDs or hashes when paragraph order is changing. Do not infer that a source is still needed because its number survived a renumbering step.

## Check Four Failure Modes

1. **Orphan source:** a retained reference is no longer cited, or is cited only for a claim that was deleted. Move it to an audit archive or document its new role.
2. **Unsupported addition:** a new claim has no source, or the cited source is only a metadata record, abstract, review, or implementation page when the claim requires original full text.
3. **Role mismatch:** the source is real but does not support the adjacent mechanism, direction, population, metric, version, or limitation at the stated scope.
4. **Citation inflation or duplication:** several citations repeat the same support without adding a distinct evidence role, or one citation is stretched across unrelated claims. Prefer the smallest set that independently supports the sentence and make separate roles visible when needed.

For every retained citation, read the neighboring sentence with the source's evidence role visible. A valid bibliographic identity is necessary but does not establish claim-level support.

## Close the Delta

After the final edit:

- recompute first-appearance numbering and reference-list order;
- verify every citation resolves and every reference is used exactly as intended;
- compare the current bibliography with the validated source map;
- recheck local full-text identity and hashes for retained or renamed files;
- record unresolved claims, unavailable originals, and deliberate exclusions rather than silently filling gaps.

The audit is complete only when the changed claims, source roles, bibliography, and reader-facing full-text package agree. If the review's conclusion changed, rerun the ledger for the conclusion and any short summary, not just the body paragraphs.
