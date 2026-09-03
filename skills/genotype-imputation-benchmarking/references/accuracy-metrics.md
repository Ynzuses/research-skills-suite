# Accuracy Metrics

## Metric Contract

For every metric, state:

- truth representation;
- imputed representation;
- unit: genotype pair, site, sample, window, or dataset;
- formula;
- aggregation and weighting;
- treatment of missing and monomorphic cases;
- allele-frequency source and bins;
- common-site or native-site evaluation rule;
- uncertainty method.

## Dosage Correlation

Distinguish at least:

- per-site squared correlation across evaluation samples;
- pooled or aggregate correlation across site-sample pairs;
- correlation of summary allele frequencies;
- software-specific model-based quality estimates.

These answer different questions. Per-site empirical dosage correlation supports window or region summaries but is undefined at sites without truth or imputed variance. Pooled correlation weights sites and samples differently and can hide local variation.

Do not call an internal model-based quality score “empirical r-squared” unless validated against truth.

## Concordance and Error Types

Overall genotype concordance can remain high for rare variants when most truth genotypes are reference homozygotes. Pair it with measures that focus on non-reference genotypes or chance-corrected agreement.

Useful outputs include:

- 3×3 truth-versus-imputed genotype confusion matrix;
- non-reference concordance or non-reference discordance;
- heterozygote sensitivity and error direction;
- Imputation Quality Score or another chance-corrected agreement measure;
- genotype-class-specific calibration.

Define NRC and NRD explicitly because published implementations differ in denominator and symmetry.

## IQS

IQS uses observed agreement and expected agreement from truth and imputed marginal genotype frequencies:

`IQS = (P_o - P_e) / (1 - P_e)`

Record how hard genotypes are derived from dosage or probabilities and how empty or degenerate strata are handled. IQS complements dosage correlation; it does not replace continuous dosage evaluation.

## Probability and Quality Calibration

For GP, dosage, INFO, DR2, or another quality output, evaluate calibration separately from discrimination. Depending on the task, report:

- reliability curve or calibration slope/intercept;
- Brier or log score;
- expected versus observed genotype accuracy;
- error rate by quality bin;
- retained fraction and accuracy after thresholds.

A high threshold that removes most difficult sites is not an unqualified accuracy gain. Report coverage or retention with the filtered metric.

## Frequency, Depth, and Region Stratification

Use biologically and statistically supported bins. Split an overly broad rare-variant bin when mechanisms or panel support change within it, but ensure sufficient allele counts and uncertainty estimates. Record whether frequency comes from the truth cohort, reference panel, target cohort, or external population.

For complex genomes, summarize sites into prespecified windows or annotations only after reporting evaluability. Use the same site and sample rules across compared strata.

## Availability Metrics

Always pair performance with:

- requested-site coverage;
- emitted-site coverage;
- evaluable-site coverage;
- genotype non-missingness;
- sample completeness;
- native versus common evaluation set.

Missing or selectively omitted sites are part of algorithm behavior, not merely a preprocessing detail.
