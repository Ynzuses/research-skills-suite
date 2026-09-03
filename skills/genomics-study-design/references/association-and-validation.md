# Association and Validation

## Input Identity

Before association analysis, verify:

- sample order and phenotype alignment;
- unique variant identifiers and allele orientation;
- chromosome code compatibility;
- tested-variant filters and defaults;
- phenotype coding and missing-value semantics;
- covariate row order and intercept behavior;
- relationship matrix population and variant set;
- software version and output field semantics.

IDs copied as missing placeholders or duplicated across variants can make extraction return the entire dataset or prevent downstream causal-site matching. Use stable composite IDs when appropriate and verify that format-conversion tools do not append an allele suffix that changes the key.

## Population Structure and Relatedness

Justify principal components, relationship matrices, family effects, or local ancestry according to the population. Report how components were selected and whether a shared matrix across compared datasets creates mismatch. Relatedness control does not automatically remove duplicated-region or mapping artifacts.

Declare whether covariates, tested-variant thresholds, transformations, model form, or significance rules are selected from the study data. If any are selected or tuned, protect held-out groups from those activities. A fixed, prespecified association analysis may mark the development–held-out split not applicable with a concrete reason, but this does not replace independent validation when the estimand claims prospective or external performance.

## Simulated Traits

For causal-variant simulations:

1. sample variants from a pool that survives the downstream test filters;
2. control frequency and genomic distribution according to the scientific scenario;
3. make the random seed and selection rule explicit;
4. map effects to the intended allele;
5. compute realized genetic values and variance components;
6. verify that major and minor components contribute the intended variance;
7. calculate expected power or at least detectability under the sample size;
8. confirm causal variants appear in the association output.

If effect sizes are intended to contribute equal genetic variance, account for allele frequency rather than assigning identical raw effects and assuming equal contribution.

## Defaults and Silent Filters

Association tools may validate phenotype columns even for apparently genotype-only operations, exclude chromosome codes, filter by allele frequency or missingness, or rewrite identifiers. Treat defaults as experimental parameters. Inspect the installed version's help and log, then specify consequential values explicitly.

## Result Interpretation

Separate:

- model ran successfully;
- prespecified technical threshold passed;
- power and calibration are scientifically adequate;
- the result is interpretable and useful for the stated research purpose.

A zero causal hit count can reflect a bug, filtered causal variants, insufficient power, or true model failure. Trace causal IDs, tested variants, and raw results before interpreting.

Repeated signals across pipelines can arise from shared upstream reference, mapping, calling, truth, or covariates. Treat cross-pipeline concordance as evidence of reproducibility, not automatic causality.

## Validation Outputs

Report as appropriate:

- genomic calibration or error rates;
- power or causal-site recovery;
- effect-size bias and uncertainty;
- distance of signals from true or known loci;
- false-positive count and distribution;
- tested-variant and evaluable-site count;
- sensitivity to population, region, frequency, and pipeline;
- limits imposed by sample size and truth quality.
