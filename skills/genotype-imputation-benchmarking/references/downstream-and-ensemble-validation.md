# Downstream and Ensemble Validation

## Downstream Utility

Genotype accuracy does not fully determine performance in GWAS, genomic prediction, or selection. Define a separate downstream endpoint and measure:

- type-I error or genomic calibration;
- power or recovery of truth-detectable loci;
- effect-size bias and standard errors;
- rank or prediction stability;
- false-positive count and distance from known causal loci;
- performance by frequency, region, and quality stratum.

Separate the power ceiling of the truth dataset from loss introduced by imputation. If the truth data cannot detect a simulated or known effect, failure after imputation cannot be assigned solely to imputation.

Represent the decision in `downstream_validation.applicability` as `required` or `not-applicable`; `open` is a planning state and cannot pass confirmation. A not-applicable decision needs a reason and no endpoints. A benchmark whose `target_use` is `downstream-analysis` cannot use that exemption.

For every required endpoint, record a stable endpoint ID, task, confirmatory or exploratory role, workflow and condition IDs, exact input fields, analysis plan, structured outcomes, status, and verification evidence. Each outcome states its definition, unit, analysis rule, and acceptance rule. Every endpoint input field must exist in every referenced workflow's declared output fields. At the strict gate, each confirmatory workflow needs confirmatory endpoint coverage and every such endpoint must be ready or completed.

## Effect Attenuation

Genotype uncertainty can bias estimated effects toward zero without proportionally increasing standard errors. Measure effect retention or attenuation at loci detectable in the truth set and relate it to local imputation quality. Do not infer the mechanism from effect size alone; allele frequency, local linkage, and site quality may dominate.

## Technical Versus Scientific Pass

Report separately:

1. structural and execution success;
2. predefined technical threshold;
3. statistical calibration and power;
4. usefulness for the intended scientific or operational task.

A benchmark can pass a minimal threshold yet remain inadequate for a publication claim or downstream application.

## Complementary Error Tests

Before selection, weighting, or gating, compare workflows on the same held-out units and evaluate:

- overlap of erroneous genotypes or sites;
- residual correlation after frequency, depth, region, and sample adjustment;
- conditional advantage by prespecified features;
- stability across folds, populations, and regions;
- calibration of workflow-specific probabilities;
- gain over the best single workflow on an untouched test set.

Different input interfaces establish only the rationale for testing complementarity.

## Layered Improvement Tasks

Keep distinct:

- variant- or window-level quality-score calibration;
- single-workflow genotype-probability calibration;
- conditional reference or workflow selection;
- cross-workflow hard selection or probability gating;
- individual-genotype residual correction using reads or local structure.

The first two do not require complementary errors. Cross-workflow gating requires stable complementarity. Individual residual correction should be attempted only when simpler calibration or selection leaves a reproducible error pattern and when the new input is leakage-safe.

## Final Confirmation

Freeze features, experts, reference choices, thresholds, and hyperparameters before opening the final confirmation set. Evaluate new individuals and new genomic regions as separate generalization axes; use their joint holdout as a stress test, not the only estimate.
