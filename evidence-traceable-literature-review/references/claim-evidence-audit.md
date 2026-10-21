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

## Full-Text Identity Check

Before linking a PDF or XML to a citation, confirm title, authors, journal or venue, year, stable identifier, version, and page or article number. Check that a commentary or perspective has not replaced the original study and that a preprint has not silently replaced a materially different final article.
