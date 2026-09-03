# Search and Screening

## Contents

- [Question Decomposition](#question-decomposition)
- [Search Ledger](#search-ledger)
- [Coverage Strategy](#coverage-strategy)
- [Deduplication and Versions](#deduplication-and-versions)
- [Screening Ledger](#screening-ledger)
- [Negative and Contrary Evidence](#negative-and-contrary-evidence)

## Question Decomposition

Define the scientific object before writing queries. Useful dimensions include population or material, intervention or method, comparator, outcome, context, study design, time, and language. Add former names, acronyms, spelling variants, implementation names, and terms used by adjacent disciplines.

Create separate query families for:

- broad discovery;
- named methods or mechanisms;
- validation and benchmark studies;
- limitations, failures, bias, or calibration;
- historical priority and citation ancestry;
- contradictory or null findings.

## Search Ledger

For every source, record:

| Field | Requirement |
| --- | --- |
| Source | Database, API, repository, publisher, or search engine |
| Date | Actual execution date |
| Query | Exact syntax submitted |
| Filters | Years, language, type, subject, access, or species |
| Boundary | Pages, cursor, result cap, or export limit |
| Raw count | Count reported by the source |
| Saved count | Records actually captured |
| Output | File or table containing raw records |

When a service truncates results or rate-limits requests, mark the search partial. Do not describe a partial repository audit as complete.

## Coverage Strategy

Use sources according to their strengths. Bibliographic databases support structured retrieval; repositories and code forges support implementation evidence; regulatory or organism databases support versioned facts; citation chaining reveals terminology changes and historical ancestry.

Search at least one source that is strong in the field's primary literature and another route capable of recovering missed terminology or implementation records when the question requires breadth. For multilingual or region-specific topics, do not assume English-language databases cover the relevant literature.

## Deduplication and Versions

Deduplicate in descending confidence:

1. DOI, PMID, accession, or another stable identifier;
2. normalized title plus first author and year;
3. manual inspection of close matches.

Keep version relationships explicit. A preprint and final article may describe the same study but are not interchangeable when methods, results, or dates changed. A perspective, editorial, protocol, correction, dataset paper, and original method paper serve different evidence roles even when their titles overlap.

## Screening Ledger

Record one row per candidate with:

- stable record ID;
- title and year;
- stage reached: retrieved, title screened, abstract screened, full text screened, included;
- inclusion or exclusion decision;
- specific reason;
- evidence role if included;
- full-text status and local mapping.

Use consistent reason codes such as wrong population, wrong outcome, no original data, inaccessible full text, superseded version, duplicate study, implementation-only record, or out of scope. Do not discard a difficult or contrary paper under a vague “irrelevant” label.

## Negative and Contrary Evidence

Maintain an explicit list of searches and studies that did not support the preferred account. Distinguish:

- no relevant record retrieved under the documented search;
- relevant records retrieved but no direct evidence found in full text;
- direct null result;
- conflicting result under different conditions;
- evidence unavailable.

Only the first two justify wording such as “this search did not identify.” Neither justifies “no study exists.”
