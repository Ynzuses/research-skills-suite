# Complex-Genome Analysis

## Keep Concepts Separate

- **Whole-genome duplication:** historical duplication event.
- **Rediploidization:** return toward disomic inheritance after duplication.
- **Delayed rediploidization:** regional timing differences in that process.
- **Residual polysomy:** current inheritance behavior requiring genetic evidence.
- **Paralogous sequence:** duplicated homologous sequence.
- **Paralogous sequence variant:** difference between paralog copies that may affect mapping or calling.
- **Repeat content:** sequence repetitiveness not equivalent to paralogy.
- **Mappability:** technical uniqueness under a defined read model.
- **Assembly collapse or error:** reference representation issue.
- **Copy-number variation:** individual or population variation in copy count.

Do not use one term as a substitute for another merely because all can create difficult regions.

## Match Analysis Scale

If the hypothesized effect is regionally concentrated, use windows, annotated segments, homologous blocks, or a multilevel model. Whole-chromosome averages can dilute a local effect and generate a false negative or misleading global story.

For each window or region, record:

- coordinates and assembly;
- callable or evaluable bases and variants;
- variant-frequency spectrum;
- coverage and mapping diagnostics;
- repeat, mappability, paralog, or duplication annotations;
- outcome metric and denominator;
- uncertainty and missingness.

Check whether evaluability itself changes with the explanatory feature. Selective loss can make retained variants look artificially accurate.

## Homology-Aware Validation

When homologous or duplicated regions may share information, group them in cross-validation or held-out splits. A model trained on one member of a homologous pair can leak sequence or annotation patterns into the held-out member.

Freeze region annotations before inspecting the outcome when the analysis is intended to be confirmatory.

## Evidence Levels

Distinguish:

- literature-defined duplicated or delayed-rediploidization regions;
- sequence-similarity proxy;
- mapping or mappability anomaly;
- genotype or heterozygosity anomaly;
- statistical association with the outcome;
- direct causal evidence.

An association between a similarity proxy and error does not prove a specific PSV mechanism without supporting mapping, variant, or experimental evidence.

## Negative or Mixed Results

If a coarse chromosome-level hypothesis is not supported:

1. report the negative result;
2. assess power, evaluability, and aggregation dilution;
3. test only prespecified finer scales in the confirmatory analysis;
4. label post hoc window or mechanism hypotheses exploratory;
5. avoid rewriting the original hypothesis as though it had predicted the new outlier.
