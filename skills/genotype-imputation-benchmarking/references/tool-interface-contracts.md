# Tool Interface Contracts

## Contract Matrix

For each installed version, capture:

| Field | Examples of what to verify |
| --- | --- |
| Target input | GT, GL, PL, BAM/CRAM, read counts, array genotypes, pedigree |
| Reference input | VCF/BCF, hap/legend/sample, binary panel, none, family |
| Genetic map | column order, header, units, chromosome naming |
| Ploidy | diploid-only, mixed ploidy, missing genotype representation |
| Region syntax | chromosome only or chromosome:start-end |
| Parallelism | actual thread parameter and threaded stages |
| Output | GT, DS, GP, INFO, DR2, quality and indexing |
| Filtering | silent site, MAF, allele, or quality exclusions |
| Version | executable hash, package version, release date |
| Failure | exit code, log marker, partial-output behavior |

Do not publish a static command as universally current. Verify the installed version's `--help`, manual, package function signature, and pilot behavior.

## Common Interface Failures

### Parameter Drift

Parameter names and semantics can change across releases. A command copied from a paper may target an older major version. Treat “unrecognized parameter” or unexpected required arguments as a version-contract issue, not a reason to guess synonyms repeatedly.

### Genetic Maps

Map formats may differ in column order, header requirements, units, marker ID, and chromosome naming. Maintain an explicit converter and validate the first and last rows, monotonic positions, and map distance.

### Ploidy and Missingness

VCF permits representations that a downstream tool rejects, such as mixed haploid and diploid missing calls in one record. Normalize ploidy only when biologically correct, then verify sample fields and record counts.

### Region Syntax and Coordinates

Some tools accept a chromosome label; others require a complete interval. Derive interval ends from the authoritative reference index and confirm contig names match the VCF and map.

### Filename Matching

Prefix globs can mix chromosome or chunk identifiers such as `1` with `10`. Use delimiter-bounded names and verify that every collected file belongs to the intended chromosome, region, depth, and workflow.

### Output Fields

Execution success does not guarantee evaluable output. As soon as the first task completes, inspect headers and records for all fields required downstream. Determine whether probabilities reflect genotype uncertainty, haplotype sharing, read evidence, or another quantity before comparing them.

### Header and Table Parsing

R, Python, Java, and command-line tools differ in whether text files require headers and how names are interpreted. Validate one row through the parser rather than assuming a syntactically valid text file is semantically accepted.

## Pilot Acceptance

Before full launch, verify:

- expected chromosome and region only;
- expected sample identities and count;
- target and emitted variant counts;
- reference and alternate alleles;
- ploidy and missing representation;
- GT, DS, GP or equivalent fields;
- internal quality fields;
- index validity and downstream readability;
- complete log and explicit success marker.

Record this check in `pilot_runs`, not only in prose or a log directory. A passed record names one registered workflow and one declared condition, stores the current `design_fingerprint`, sets both pilot state and output-validation status to `passed`, lists every verified output field, and cites evidence. The workflow-condition pair must occur in `required_comparisons`. A process exit code alone cannot satisfy output validation.

If a workflow changes executable identity, registered inputs, reference context, transductive status, tuning budget, output fields, or failure policy, its old pilot no longer proves the current interface. Mark the record `stale` or retain it as historical evidence, run a new complete unit, and bind the new result to the updated design fingerprint.
