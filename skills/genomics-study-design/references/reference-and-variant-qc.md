# Reference and Variant QC

## Reference Contract

Record:

- assembly name, accession, version, and provider;
- annotation release and gene-model source;
- chromosome and contig naming;
- primary, alternate, unplaced, organellar, and sex-linked sequences;
- gap, mappability, repeat, and known paralog resources;
- source individual ploidy, sex, strain, or haplotype when relevant;
- checksums and retrieval date;
- coordinate conversion or lift-over method for historical loci.

Verify named genes and regions against the exact assembly. A command can return plausible coverage at a wrong coordinate, so successful execution does not validate locus identity.

## Sample and Metadata Contract

Use stable accessions or compound keys rather than mutable aliases alone. Reconcile run, sample, individual, population, family, sex, batch, platform, library, and coverage fields. Record inferred metadata separately from directly reported metadata.

Do not overstate platform, depth, or cohort uniformity. Distinguish nominal raw depth, mapped depth, duplicate-marked depth, callable depth, and effective analysis depth.

## Mapping and Calling

First decide whether the study owns mapping and calling. `variant-discovery` always does. A study that begins from a fixed genotype resource or only audits a reference may declare the module not applicable with a concrete reason and no tool or path payload. If the study remaps any reads, recalls any sites, changes joint-genotyping membership, or regenerates callable space, the module is applicable.

For an applicable module, make explicit:

- read preprocessing and adapter policy;
- reference index and aligner version;
- duplicate marking versus removal;
- mapping and base-quality thresholds;
- ploidy and sex-chromosome assumptions;
- per-sample calling and joint genotyping design;
- interval partition and merge order;
- representation normalization and multiallelic handling.

Parallelize independent intervals or samples where safe, but verify that merges preserve ordering, headers, sample sets, and unique keys.

## Layered QC

Separate:

1. read-level quality;
2. alignment-level quality;
3. variant-site quality;
4. genotype-level quality;
5. population-level plausibility;
6. analysis-specific eligibility.

A site-level hard filter and a genotype-level confidence mask answer different questions. Applying both may be appropriate, redundant, or destructive depending on empirical distributions and downstream use.

## Stepwise Filter Audit

After each filter, record:

- sites and genotypes before and after;
- proportion removed;
- missingness change;
- allele-count or frequency change;
- transition/transversion or other diagnostic where interpretable;
- distribution by chromosome, window, sample, batch, or ploidy class;
- reason and downstream dependency.

Bind the count record to the individual destructive QC rule as well as to the overall discovery workflow. This keeps an existing-genotype or association-only study auditable without pretending that it performed upstream mapping and calling.

An extreme one-step loss is a stop signal. Inspect the affected quality distribution and assumptions before continuing.

## Species-Aware Thresholds

For every consequential threshold:

1. identify its source and intended organism or dataset;
2. inspect the target distribution;
3. connect the metric to the target genome's biology and technical properties;
4. compare candidate thresholds and downstream consequences;
5. document the selected rule and uncertainty.

Do not use “standard” as the only rationale. Human defaults, diploid assumptions, and canonical chromosome maps often fail in non-model or duplicated genomes.
