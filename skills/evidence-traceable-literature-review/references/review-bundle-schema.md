# Review Bundle Schema

Use this reference when creating, extending, or validating the optional machine-readable evidence bundle. Copy the four header-only TSV templates from `assets/` into the bundle and add one record per row. Save every file as strict UTF-8 with tab delimiters. The templates contain no study data or personal information.

Run the read-only validator from the Skill directory:

```text
python scripts/validate_review_bundle.py --bundle review-bundle --format text
```

Use `--format json` for automation. Exit status is `0` when there are no errors, `1` for a structurally invalid bundle, and `2` for command-line or file-reading failures. Warnings do not change a successful exit status unless a documented release-strict mode says otherwise.

Before publishing or handing off a bundle, run:

```text
python scripts/validate_review_bundle.py --bundle review-bundle --format json --strict-release
```

`--strict-release` requires a matching SHA-256 for every `present` full text and promotes every validator warning to an error. This is an intentionally closed release gate: orphan package members, included-but-unused sources, missing counts for a complete search, invalid package directories, and any warning introduced by a future validator version must be resolved or explicitly kept out of release mode. The validator is read-only in both modes.

## Table Contracts

- `search-ledger.tsv`: `search_id` is unique. `source`, ISO `executed_date`, exact `query`, and `status` are required. Status is `complete`, `partial`, or `failed`; counts, when present, are non-negative integers. A complete search must give both counts or leave both blank, and `saved_count` cannot exceed `raw_count`. Leaving both blank is accepted with a warning because the count relationship cannot be audited; release-strict mode therefore rejects it. Partial and failed searches may leave either count blank when the backend did not return a reliable value.
- `screening-ledger.tsv`: each unique `record_id` identifies one decision event and `search_id` must resolve to the search ledger. `stage` is `retrieved`, `title`, `abstract`, or `full_text`; `decision` is `include`, `exclude`, or `pending`. `decision_round` is a positive integer and `current` is exactly `true` or `false`. `supersedes` is blank or a semicolon-delimited list of earlier `record_id` values. Every reference must resolve, point to the same non-empty `source_id`, have a lower decision round, and identify a `current=false` row; cycles, branching successors, and self-references are rejected. Each source with screening rows has exactly one current decision, and every historical row must be reachable through that current row's supersession closure. Thus an old include followed by a current exclude is excluded, rather than being ambiguously revived by its history. Included rows require a resolvable `source_id` and an evidence role. Excluded rows require a reason. Any versioned history requires `source_id` on all participating rows, and every non-empty `source_id` resolves to the source manifest.
- `evidence-matrix.tsv`: `evidence_id` uniquely identifies one claim-source relationship. `claim_id` may repeat so independent or contrary sources can attach to the same stable claim; repeated definitions must keep the same `claim_text` and `claim_status`. Every row requires a resolvable included `source_id` and a page, section, table, figure, supplement, line, or equivalent `locator`.
- `source-manifest.tsv`: `source_id` is unique. `citation`, `evidence_role`, and `full_text_status` are required. Status is `present`, `unavailable`, or `not_required`. A present full text requires an existing regular-file path relative to the bundle. Absolute paths, parent traversal, and symlink escape are rejected. SHA-256 values contain 64 hexadecimal characters and, when supplied, must match the file; they are mandatory in release-strict mode. Paths and hashes stay blank for unavailable or not-required full text.

Evidence and source roles use `original_study`, `validation`, `review`, `database`, `software`, `background`, or `other`. Claim status uses `fact`, `synthesis`, `hypothesis`, `method_decision`, or `unresolved`. Direction uses `supports`, `contradicts`, `limits`, or `does_not_address`; strength uses `direct`, `indirect`, `triangulating`, or `insufficient`; intended use uses `background`, `method`, `result`, `limitation`, `interpretation`, or `other`.

Put deliverable full texts below `full-text/` or `full_text/` to enable orphan-package-member warnings. An included source unused by any valid claim-source relation is also a warning. Missing evidence, duplicate IDs, unresolved relationships, invalid paths, missing files, and hash mismatches are errors. These checks establish package integrity only; they do not judge the scientific truth or sufficiency of a claim.

## Schema Compatibility

The TSV header is the versioned machine contract. The current `screening-ledger.tsv` adds `decision_round`, `current`, and `supersedes`; older ten-column screening ledgers are intentionally not guessed or silently upgraded. They fail deterministically with `header_mismatch`. To migrate, add the three columns in the template order, assign one `current=true` event per source, mark earlier events `current=false`, and connect all earlier events to the current event through valid `supersedes` references. Header-only bundles should be refreshed by copying the current templates. This strict failure is preferable to treating historical include and exclude rows as simultaneously current.
