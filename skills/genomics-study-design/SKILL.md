---
name: genomics-study-design
description: "Design and audit non-model, polyploid, duplicated, or non-human genomic studies. Use when a task needs reference assemblies, truth sets, mapping, variant discovery, species-aware QC, paralogy or WGD, leakage, population or GWAS validation, trait simulation, or diagnosis of unexpected signals. Compose with evidence and statistics skills. Do not use for one command or generic biology."
---

# Genomics Study Design

## Purpose

Translate a biological question into a species-aware, versioned, leakage-controlled genomics design. Make reference choice, coordinate system, sample structure, variant QC, analysis scale, and validation explicit rather than inheriting human-genome defaults.

## Establish the Study Contract

Choose one `study_mode` before filling operational modules:

- `variant-discovery` for studies that map reads and discover or jointly call variants;
- `existing-genotypes` for studies beginning from an existing genotype call set;
- `association-only` for a fixed association or downstream analysis that does not own upstream calling;
- `reference-audit` for assembly, annotation, coordinate, or reference-resource verification.

Then record:

- biological question and estimand;
- organism, ploidy, genome history, population, and tissue or sample context;
- reference assembly, annotation release, coordinate system, and chromosome naming;
- sample inclusion, relatedness, batch, family, sex, population, and truth status;
- mapping and variant-discovery details when the selected mode owns those operations;
- whether data-dependent threshold, feature, reference, covariate, parameter, or model selection occurs;
- a development and held-out split whenever such selection occurs, or a concrete reason it is not applicable;
- expected tables, figures, diagnostics, and uncertainty;
- privacy, database, and publication boundaries.

Use authoritative databases and primary literature to verify assembly and locus facts. A coordinate without an assembly version is incomplete.

For an executable, multi-stage, or audited study, instantiate [STUDY_CONTRACT.json.template](assets/STUDY_CONTRACT.json.template). Preserve species- or platform-specific additions in `extensions` while keeping common reference, sample, truth, split, scale, QC, hypothesis, evidence, output, and validation fields comparable. Use `applicability: "not-applicable"` only with a concrete `reason`; leave the module's tool, path, group, and verification fields null or empty rather than inventing sentinel values. Read [study-contract-modes.md](references/study-contract-modes.md) for mode selection, conditional-module rules, and the stable ID closure.

Validate structural closure with:

```text
python scripts/validate_study_contract.py study-contract.json
```

The validator catches missing versions, unresolved or orphaned IDs, incompatible declared scales, false not-applicable records, and incomplete leakage/QC records. It does not establish biological truth, decide whether a module is scientifically applicable, or approve a threshold.

## Run the Workflow

### 1. Define the Biological Object and Scale

Separate the latent biological process from its proxy, annotation, or quality signal. State whether the hypothesis operates at read, genotype, site, window, gene, homologous block, chromosome, individual, family, or population level.

A chromosome-wide mean cannot establish a local duplication, paralog, mappability, or assembly effect. Use windows or annotated regions when the mechanism is local.

### 2. Verify Reference and Coordinates

Confirm assembly accession and version, annotation release, contig naming, gap or alternate representation, source individual attributes when relevant, and the mapping between historical and current coordinates. Do not reuse a locus coordinate from another assembly without lift-over or independent validation.

Read [reference-and-variant-qc.md](references/reference-and-variant-qc.md) for reference and QC contracts.

### 3. Design Samples and Truth Sets

Define stable sample or audited-record keys and reconcile metadata across archives. Explicitly declare whether reference construction, parameter tuning, feature selection, threshold choice, covariate choice, or model selection is data dependent. When it is, split samples or groups first and block related individuals, batches, populations, repeated measures, homologous regions, and other leakage routes at the appropriate group level. A study with no such choice may mark the split not applicable with a concrete reason, but absence of tuning does not waive an independent evaluation required by the estimand.

State whether “truth” is orthogonal, high-depth, array-derived, consensus, or simply the best available output from a shared upstream pipeline. Shared upstream calling creates a relative benchmark, not absolute biological truth.

### 4. Build Mapping and Variant-Discovery Diagnostics

For `variant-discovery`, record aligner, caller, versions, ploidy assumptions, interval strategy, duplicate handling, joint-calling design, callable space, and stepwise counts; these are hard requirements. For a mode that starts from existing calls or audits only a reference, mark the module not applicable only when the study truly does not own mapping or calling and state why. Preserve per-rule stepwise counts for every destructive QC operation so an anomalous loss can be assigned to one operation.

### 5. Calibrate QC Empirically

Treat each threshold as a hypothesis about the target organism and data. Inspect the metric distribution and biological meaning before adopting a human or model-organism convention. Distinguish read-, site-, genotype-, and population-level filters and avoid redundant filters that destroy usable variation without independent benefit.

Software defaults are part of the study design. State consequential defaults explicitly and verify the installed version's behavior.

### 6. Analyze Complex-Genome Features Conservatively

Keep whole-genome duplication, delayed rediploidization, residual polysomy, paralogous sequence variation, repeat content, mappability, assembly collapse, copy number, and homology annotations conceptually distinct. Each requires its own evidence.

Read [complex-genome-analysis.md](references/complex-genome-analysis.md) for windowed and homology-aware analysis.

### 7. Design Association or Downstream Validation

Specify variant IDs, allele orientation, phenotype coding, covariates, relationship matrix, population structure, sample exclusions, tested-variant filters, multiple-testing rule, and power. For simulated traits, ensure causal variants survive downstream filters and verify realized variance components.

Read [association-and-validation.md](references/association-and-validation.md) for GWAS, trait simulation, and interpretation checks.

### 8. Interpret from Competing Hypotheses

When an unexpected signal appears, test technical, design, statistical-power, biological, and scale-mismatch explanations against primary artifacts. Do not label a reproducible cross-pipeline signal biological merely because it repeats; shared reference, alignment, calling, or annotation can reproduce the same artifact.

## Non-Negotiable Rules

- Every coordinate is tied to an assembly and annotation version.
- Species-aware QC begins with observed distributions and intended use, not inherited thresholds.
- Stepwise counts are required for destructive filters.
- Shared-pipeline truth is described as a baseline, not absolute truth.
- Local or duplicated-genome hypotheses require local or hierarchical analysis.
- A plausible WGD or paralog mechanism remains a hypothesis until region-level evidence supports it.
- Whenever selection or tuning occurs, held-out groups remain isolated from every declared selection activity.
- Consequential software defaults and silent filters are made explicit.
- Cross-species absolute performance comparisons require commensurate data, truth, and metrics.
- An inapplicable module carries a concrete reason and no fabricated tool, path, group, or verification value.
- Every hypothesis resolves through declared evidence IDs to structured outputs and evidence-linked validations.

## Stop or Ask When

Pause when study mode or assembly identity is unresolved, sample or population labels conflict, a required module is incorrectly marked not applicable, the proposed split leaks held-out information, a threshold would remove most data without a validated rationale, or a requested biological interpretation cannot be distinguished from technical artifacts with available evidence.

## Completion Standard

A genomics design is complete when its mode-specific structural contract closes, reference and coordinates are versioned, sample and truth roles are explicit, applicable operations are fully specified, inapplicable operations are justified without fake values, QC and defaults are supported by diagnostics, hypotheses match the analysis scale and resolve to validated outputs, leakage paths are blocked where selection occurs, downstream tests are internally coherent, and alternative explanations remain visible.
