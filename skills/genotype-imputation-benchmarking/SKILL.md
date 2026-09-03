---
name: genotype-imputation-benchmarking
description: "Design, run, diagnose, and audit genotype-imputation benchmarks across low coverage, arrays, panels, families, or reference-free workflows. Use when a task needs data contracts, leakage control, stratification, evaluability, accuracy, calibration, downstream GWAS, or complementary-error testing. Do not use for generic genotype QC or one-tool installation."
---

# Genotype Imputation Benchmarking

## Purpose

Create fair, reproducible imputation comparisons that respect each workflow's information interface while preserving a common scientific question, independent truth, explicit evaluability, and claim-level metric definitions.

## Establish the Benchmark Contract

Record:

- target use: genotype recovery, low-coverage sequencing, array densification, reference-panel evaluation, family imputation, or downstream analysis;
- target samples, population, ancestry, relatedness, and ploidy;
- truth definition and how it is hidden from development;
- reference panel or reference-free learning set;
- target-site universe and common evaluation space;
- depth, density, allele-frequency, region, and population conditions;
- allowed input for each workflow;
- software versions, tuning budget, failure rules, outputs, and compute metrics.

For a benchmark that will be executed, compared, resumed, or audited, instantiate [BENCHMARK_CONTRACT.json.template](assets/BENCHMARK_CONTRACT.json.template). The portable data shape is defined by [BENCHMARK_CONTRACT.schema.json](assets/BENCHMARK_CONTRACT.schema.json); keep method-specific additions under the nearest declared `extensions` object instead of changing common field meanings. Validate the planning contract before piloting:

```text
python scripts/validate_benchmark_contract.py benchmark-contract.json
```

This validator checks registry and ID closure, comparison coverage, pilot identity, output-field compatibility, downstream endpoint declarations, and leakage state. It does not certify that a truth set is biologically valid, a split blocks every information path, or a metric answers the scientific question; those remain scientific audits.

Use ordinary validation while the benchmark is being scoped or piloted. Safe unresolved states such as an open input, a null workflow role, a planned pilot, or open downstream applicability produce warnings rather than optimistic defaults. Its report contains two deterministic SHA-256 values:

- `design_fingerprint` covers the current design while excluding runtime `pilot_runs` and the self-referential final lock. Copy it into a pilot only after the input registry, workflow, truth boundary, conditions, metrics, comparisons, downstream design, and output schema are current.
- `confirmatory_fingerprint` covers the complete contract including pilot evidence while excluding only `confirmatory_lock`. Copy it into the lock only after current pilots and all confirmatory declarations are closed.

Before opening final evaluation data, mark every workflow explicitly confirmatory or non-confirmatory, verify the authority and version of every input used by a confirmatory workflow, assert that none contains evaluation truth, and run at least one representative end-to-end pilot for each confirmatory workflow. A passed pilot must cite validation evidence and verify every declared output field. Resolve every leakage channel and, when downstream validation is required, define confirmatory endpoints whose input fields are actually emitted by their workflows. Rerun ordinary validation, copy the reported `confirmatory_fingerprint` into the lock, set `status` to `frozen`, record that freezing preceded final evaluation, cite the freeze evidence, and then run:

```text
python scripts/validate_benchmark_contract.py benchmark-contract.json --strict-confirmatory
```

Strict confirmatory mode fails when a confirmatory workflow uses an unknown, retired, open, or truth-bearing input; lacks a passed pilot bound to the current design; has unresolved output fields; lacks required downstream endpoint coverage; leaves a leakage channel open or omitted; or has an open, missing, or stale final lock. Keep the template's lock open and risky decisions null during drafting; unresolved state is representable but cannot pass the confirmatory gate.

Distinguish a single end-to-end workflow from a post hoc combination of completed workflows. Machine learning is an implementation tool that can serve calibration, selection, gating, or residual correction; it is not a peer category to workflow scope.

If the study contract explicitly requires machine-learning training or another method family, record that requirement separately from the still-open choice of module, architecture, or hyperparameters. Do not demote required training to an optional post hoc task merely because machine learning is an implementation tool; locate the trainable component on the internal imputation computation and keep the statistical baseline explicit.

State the optimization object before selecting comparisons: an internal imputation algorithm, an end-to-end pipeline, an output-quality model, a multi-workflow ensemble, or a downstream decision rule. If the claimed contribution is algorithmic, define the internal module being changed and treat pipeline sequencing, thresholds, calibration, voting, weighting, and gating as baselines or diagnostics unless they are explicitly the research object. Do not let a benchmark of available software silently replace a planned source-level algorithm improvement.

## Run the Workflow

### 1. Classify Information Interfaces

For each candidate, identify whether the target enters as hard genotypes, genotype likelihoods, read data, allele counts, array genotypes, pedigrees, or jointly learned low-coverage haplotypes. Identify whether external reference haplotypes, study samples, families, or learned population structure supply the inference context.

Do not call methods comparable merely because they all output genotypes. State whether the benchmark compares algorithms under common inputs or complete pipelines under native inputs.

When explaining candidate algorithms or source-level modifications, establish the computation before naming modules: observed reads or genotypes -> likelihoods or other evidence -> reference or learned candidate states -> transitions or updates -> GP, DS, GT, or another output. Define first-use abbreviations and specialist terms in plain language, then identify the exact internal object they change. Distinguish internal inference changes from downstream filtering, calibration, voting, weighting, and gating.

Introduce a specialist label only when it is needed for the current comparison or will be reused. If an overview does not use a named emission, gate, residual, or ablation to make a decision, omit the label and explain it later at the first functional use. For every trainable internal component, record its input, training target or supervision, loss or update rule, parameters changed, output, and the imputation stage that consumes that output.

### 2. Freeze Truth and Prevent Leakage

Split development and evaluation before reference construction, phasing, parameter tuning, target-site selection, quality calibration, or model training. Block related individuals, populations, batches, homologous regions, and other information paths as required.

Reference-free or study-sample methods can be transductive: evaluation-sample low-coverage data may help learn shared haplotypes. Report that design separately from an external-panel benchmark and keep high-depth truth hidden.

Read [benchmark-design.md](references/benchmark-design.md) for fair comparison and leakage controls.

### 3. Build a Versioned Interface Matrix

For every workflow, record exact executable or package version, command interface, required input fields, ploidy, chromosome and region syntax, genetic-map format, reference format, output fields, internal quality metric, and failure behavior.

Verify the installed version's help and a pilot output. Literature examples and old tutorials can use obsolete parameter names or different formats.

Read [tool-interface-contracts.md](references/tool-interface-contracts.md) before full execution.

### 4. Pilot One Complete Unit

Run one representative chromosome, chunk, depth, or sample through the entire pipeline. Inspect output sample count, variant count, chromosome identity, alleles, GT/DS/GP or equivalent fields, quality score, indexing, and downstream compatibility before launching all units.

Bind each pilot to the validator's current `design_fingerprint`, its `workflow_id`, and a `condition_id` paired with that workflow in `required_comparisons`. A change to inputs, reference construction, executable version, target universe, output schema, truth isolation, metric definition, failure rule, comparison, or downstream design changes that fingerprint and invalidates the earlier pass; mark it stale and rerun it rather than inheriting approval.

### 5. Define Metrics Before Seeing Rankings

Specify formula, truth and imputed representation, unit of analysis, aggregation, missingness, monomorphic handling, allele-frequency source, bins, and common-site rule. Pair discrimination metrics with error-type, calibration, and evaluability metrics.

Read [accuracy-metrics.md](references/accuracy-metrics.md) for metric design.

### 6. Stratify by the Mechanism of Difficulty

Report performance by relevant dimensions such as allele frequency or count, depth, ancestry, reference-panel size, sample, chromosome, window, mappability, duplicated or homologous region, and genotype class. Do not let a genome-wide average stand in for a local complex-region hypothesis.

### 7. Evaluate Output Availability and Selection

Report target sites requested, sites emitted, sites evaluable, genotype non-missingness, and any internal filtering. A method that omits hard sites can look accurate on the retained subset. Compare performance on both native reported sites and a clearly defined common evaluation set when possible.

### 8. Validate Downstream Use

When the research question concerns GWAS, genomic prediction, or another downstream task, measure calibration, power or recovery, effect-size bias, ranking stability, and false positives in addition to genotype accuracy.

Read [downstream-and-ensemble-validation.md](references/downstream-and-ensemble-validation.md) for downstream and complementarity tests.

### 9. Interpret Without Overreach

Separate algorithm behavior, input information, reference-panel size and ancestry, preprocessing, internal site selection, truth imperfection, and genome complexity. Do not attribute a performance gap to one mechanism without evidence that distinguishes these alternatives.

For source-level innovation, require a matched original-versus-modified comparison with the same inputs, reference, evaluation set, and compute budget, followed by module ablations. Exceeding another software package does not identify which code change caused the gain; an external ensemble or calibrated score does not demonstrate improvement of the underlying imputation algorithm.

## Non-Negotiable Rules

- Each workflow has an explicit input-output contract.
- The optimization object and claimed contribution remain fixed from benchmark design through interpretation.
- Every proposed internal module is tied to the input or intermediate object it changes and to an observable output; a list of mechanism labels is not an explanation.
- Installed-version behavior outranks copied command examples.
- High-depth or orthogonal truth never enters tuning, phasing, reference construction, or target-site choice.
- Information-source differences imply possible, not proven, complementary errors.
- Accuracy is reported with evaluability and missingness.
- Concordance alone is insufficient when rare variants are in scope.
- Metric labels are not compared until formulas, filters, denominators, and aggregation match.
- Region or WGD hypotheses are tested at window or annotated-region scale, not inferred from whole-chromosome averages alone.
- A technical pass threshold is not automatically a scientifically adequate benchmark.

## Stop or Ask When

Pause if truth leaks into development, workflows are given incomparable privileges without an explicit end-to-end framing, output fields required for evaluation are absent, a method silently drops most target sites, population or panel identity is unclear, or a fallback changes the benchmark question.

## Completion Standard

A benchmark is complete when the machine-readable contract closes, candidate workflows have versioned interfaces, truth and evaluation are isolated, pilot and full outputs pass structural checks for the current contract, metrics and bins are predefined, performance and evaluability are reported together, downstream claims are separately validated, and mechanistic interpretations remain within the evidence.
