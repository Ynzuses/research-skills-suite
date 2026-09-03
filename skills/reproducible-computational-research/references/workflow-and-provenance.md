# Workflow and Provenance

## Separate Evidence Layers

Maintain distinct records for:

1. **Scientific design:** question, variables, estimand, assumptions, and analysis plan.
2. **Data truth:** immutable inputs, identifiers, schemas, units, filters, and access class.
3. **Code truth:** scripts, configuration, versions, parameters, and dependency lock.
4. **Execution state:** submitted, running, failed, complete, retried, superseded.
5. **Artifact truth:** files, row counts, hashes, timestamps, completeness, and lineage.
6. **Narrative state:** claims, figures, tables, manuscripts, and decisions based on artifacts.

A workflow diagram or project status note cannot substitute for physical output checks, and a Git commit cannot prove the contents of ignored results.

## Artifact Contract

For each stage, define:

| Field | Requirement |
| --- | --- |
| Inputs | Exact paths or identifiers, versions, hashes, and schema |
| Transformation | Script, configuration, executable, and parameters |
| Outputs | Expected filenames, schema, units, and counts |
| Completion role | Whether each output is required for the stage's completion claim |
| Success | Content and completion invariants |
| Failure | Exit conditions and diagnostic locations |
| Restart | Safe skip, retry, cleanup, and rollback behavior |
| Consumers | Downstream scripts, figures, tables, or documents |
| Access | Public, restricted, private, or derived-sensitive |

## Data Before Narrative

Before output exists, it is safe to specify fields, analysis units, models, and planned figures. It is not safe to prewrite numerical conclusions, hard-code an expected ordering, or make a plotting layer depend on idealized data behavior.

Once data exist, trace each reported number to one authoritative table or deterministic computation. Recalculate through the same workflow when corrections are required; do not patch the manuscript from an unrelated interactive calculation.

## Metric Identity

For every metric, record formula, unit, aggregation level, denominator, weighting, filter, missingness rule, and evaluation set. Two tables labeled with the same metric are not interchangeable when any of these differ.

## Handoff Evidence

Useful completion evidence includes:

- expected versus observed file count;
- row and column counts;
- unique key count and duplicate count;
- first and last expected unit;
- timestamp relative to upstream inputs;
- content hash or checksum;
- completion marker and exit code;
- sampled or full invariant checks.

Report unresolved or stale outputs separately from complete outputs.
