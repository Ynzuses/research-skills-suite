# Claim-to-Evidence Audit

## Evidence Ledger

Use one row per material claim-source relationship:

| Field | Content |
| --- | --- |
| Claim ID | Stable identifier used in prose notes |
| Claim | Exact statement being supported |
| Claim status | Fact, synthesis, hypothesis, method decision, or unresolved |
| Source identity | Full citation and stable identifier |
| Source role | Original study, validation, review, database, software, or background |
| Locator | Page, section, paragraph, table, figure, supplement, or line |
| Evidence excerpt | Short paraphrase or minimal quotation necessary for audit |
| Scope | Population, dataset, version, metric, and conditions |
| Direction | Supports, contradicts, limits, or does not address |
| Strength | Direct, indirect, triangulating, or insufficient |
| Intended use | Background, method, result, limitation, or interpretation |

Avoid retaining long copyrighted passages. Store a precise paraphrase plus locator unless a short quotation is necessary.

## Verification Rules

### Scientific Existence Claims

For claims that a method, value, variable, or analysis appears in a paper, search the complete text and supplements using case-insensitive terms, abbreviations, synonyms, and nearby concepts. A paper that never contains the asserted data or method is a hard mismatch, even if its topic is adjacent.

### Numerical and Directional Claims

Confirm the unit, denominator, sign, comparison direction, scale, and order of magnitude. Verify whether the value is observed, simulated, recommended, default, or merely tested. Do not convert a tested threshold into an endorsed threshold.

### “First,” “Earliest,” and Novelty

Inspect the candidate paper's introduction, related work, and cited predecessors. Follow citation ancestry to the earliest work that actually performed the claimed task. Distinguish first proposal, first implementation, first validation, first use in a domain, and first open-source release.

### Method and Software Claims

Separate the scientific model from a particular software implementation and version. Verify current parameters against the installed version's help or official documentation; literature examples may describe older interfaces.

### Reviews and Secondary Sources

Use reviews to map terminology, influential studies, and disputes. Return to primary studies for consequential effect sizes, mechanisms, limitations, or method details. If only secondary evidence is available, label it as such.

### Absence Claims

Document the search space and exact terms. Use “not identified in this search” or “not established by the retrieved evidence.” Do not use “does not exist” unless an authoritative, bounded registry directly supports that statement.

## Evidence Strength and Wording

- Direct measurements support “measured,” “observed,” or “estimated.”
- Repeated compatible studies support a bounded synthesis.
- Mechanistic consistency supports “is consistent with” or “suggests.”
- Indirect analogy supports a hypothesis, not an established effect.
- Conflicting studies require conditions and uncertainty, not majority voting alone.

## Independent Verification Pass

The reader who wrote a sentence tends to find its support in the source. Before a review is circulated, have each material claim checked by a verifier that did not draft it.

- Give the verifier the claim as worded in the document, the cited source's full text, and the locator if one is recorded. Withhold the drafting notes and the author's reasoning.
- The verifier searches the full text and supplements itself and returns one outcome per claim-source pair, using the ledger's existing fields:

| Outcome | Direction | Strength | What the verifier must return |
| --- | --- | --- | --- |
| Supported as worded | supports | direct | locator and a short paraphrase of the passage |
| Supported only in part, or under narrower conditions | limits | direct or indirect | locator, and which part of the wording exceeds the source |
| Contradicted | contradicts | direct | locator of the conflicting passage |
| Not found in the source | does not address | insufficient | the terms and sections searched |
| Could not be checked | leave unchanged | leave unchanged | the reason, such as no full text, an unreadable file, or a missing supplement |

- “Could not be checked” is not support. The claim keeps its earlier status and stays on the open list until someone reads the source.
- A verifier's outcome is a finding to confirm, not a ruling. For every outcome other than full support, open the source at the returned locator before changing the document. A verifier can misread a table or miss a supplement as easily as an author can.
- Repair the wording, replace the source, or remove the claim, then recheck the short forms that repeat it: abstract, table, conclusion, and summary.
- When the same kind of mismatch appears in several claims, treat it as a pattern and recheck the remaining claims of that kind.

A verifier from a different model family adds the most independence. If task content would leave the machine to reach it, apply the workspace's privacy rule to the claim text and to the source before sending either.

## Full-Text Identity Check

Before linking a PDF or XML to a citation, confirm title, authors, journal or venue, year, stable identifier, version, and page or article number. Check that a commentary or perspective has not replaced the original study and that a preprint has not silently replaced a materially different final article.
