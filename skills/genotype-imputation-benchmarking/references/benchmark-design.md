# Benchmark Design

## Define Comparable Objects

Decide whether the study compares:

- algorithms under identical inputs;
- native end-to-end workflows under their intended inputs;
- reference panels or panel-selection strategies;
- quality calibration or post-processing models;
- single workflows versus cross-workflow combinations.

Do not mix these levels in one ranking without labeling them. A read-aware pipeline and a hard-genotype pipeline may be fairly compared as end-to-end strategies, but the performance difference cannot be assigned to the imputation kernel alone.

## Truth Hierarchy

Possible truth sources include orthogonal arrays, high-depth sequencing, validated pedigrees, consensus calls, or shared-pipeline high-depth calls. Record genotype confidence, missingness, platform, variant representation, and whether the same reference or caller created correlated errors.

“Truth” from the same upstream mapping and variant-calling pipeline is a best-available baseline, not an absolute biological truth.

## Split and Leakage Controls

Prevent evaluation samples or their near relatives from entering:

- reference-panel construction or expansion;
- phasing or model fitting when independence is claimed;
- parameter and threshold tuning;
- target-site selection;
- quality calibration or ensemble training.

Group related individuals, repeated samples, populations, batches, and homologous regions as needed. Evaluate new-sample and new-region generalization separately; combine them only as a deliberate stress test.

## Transductive Workflows

Some reference-free or joint-sample methods learn ancestral haplotypes from the low-coverage target cohort. This can be scientifically valid, but it changes the estimand:

- allow only the low-coverage data specified by the workflow;
- keep high-depth or orthogonal truth masked;
- freeze K, iterations, target sites, QC, and stopping rules using development data;
- label the comparison transductive rather than external-reference independent;
- do not claim performance for a new isolated sample without a separate test.

## Reference Panels

Record panel size, ancestry, population composition, relatedness, sequencing or array platform, calling pipeline, phasing method, variant set, and version. Separate panel size effects from ancestry-match effects. A larger mismatched panel may underperform a smaller matched panel, especially for rare variants.

## Tuning Fairness

Give each workflow a predefined, defensible tuning budget. Use native recommended inputs and parameters when the comparison is end-to-end, but disclose privileges such as reads, pedigrees, or study-sample learning. Freeze success, failure, retry, and fallback rules before inspecting final rankings.

For a confirmatory evaluation, first close `input_registry`: every input used by a confirmatory workflow has a stable authority and version, verification evidence, and an explicit `contains_evaluation_truth: false` declaration. IDs in workflow `input_ids` must resolve to this registry; a free-text list of allowed inputs is not an auditable boundary.

Resolve leakage channels and validate the complete design while final evaluation remains hidden. The validator's `design_fingerprint` excludes runtime pilots and the final lock, so each representative passed pilot can bind the exact design it exercised. After the current pilot evidence and downstream declarations are present, record `confirmatory_fingerprint` in a frozen `confirmatory_lock` before opening final results. That second fingerprint includes pilots and excludes only the self-referential lock. Changing the design makes the pilot stale; changing either design or pilot evidence invalidates the final lock. Rerun and explicitly refreeze rather than silently inheriting the earlier confirmation.

## Output Availability

For every workflow and stratum, report:

- requested target variants;
- emitted variants;
- evaluable variants;
- missing genotypes or dosages;
- sample completeness;
- internally filtered records;
- overlap with the common evaluation set.

Distinguish “not emitted,” “emitted but missing,” “not polymorphic,” and “metric undefined.”
