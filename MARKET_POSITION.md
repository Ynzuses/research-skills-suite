# Product Position and Retention Audit

Reviewed 2026-08-20. This is a release-positioning audit, not a claim that no comparable implementation can exist.

## Decision

Retain all eight Skills in the first suite release. They solve distinct user goals, but they should not receive equal homepage emphasis.

| Skill | Release role | Adjacent public category | Defensible differentiation | Retention decision |
| --- | --- | --- | --- | --- |
| `manage-workspace-memory` | Flagship | memory banks, repository instructions, project notes | infers a project-aware authority/directory blueprint; typed truth ownership; three-hop recovery; event-driven minimal maintenance; frozen identities; deterministic drift audit | Retain and lead |
| `evidence-traceable-literature-review` | Flagship | literature search and review generation | primary-full-text claim ledger, contrary evidence, resume cursor, citation-delta propagation, and bibliography-to-source-package identity closure | Retain and lead |
| `research-document-delivery` | Flagship | Word/PDF editing and conversion | authority direction, recoverable review adjudication, OpenXML comment/people closure, semantic run preservation, current-hash rendering records, and submitted-baseline branching | Retain and lead |
| `genotype-imputation-benchmarking` | Vertical flagship | genomics pipelines and generic benchmarking | workflow information interfaces, transductive/reference framing, truth leakage controls, native/common evaluation universes, evaluability, calibration, downstream validity, and matched source-level ablations | Retain and lead to specialist users |
| `scientific-writing-and-revision` | Specialist | scientific writing and editing | purpose-drift recovery, epistemic-status ledger, feedback adjudication, global defect propagation, structural prominence, and short/long-form parity | Retain with narrow argument/revision positioning |
| `genomics-study-design` | Specialist | general genomics analysis | non-model and non-human defaults, assembly/coordinate contracts, ploidy and duplicated-genome reasoning, local-scale hypotheses, empirical QC, and shared-pipeline truth limits | Retain |
| `reproducible-computational-research` | Specialist | reproducibility and HPC workflow guidance | explicit missing/partial/stale/failed/verified-zero state, quantitative checkpoints, single-source outputs, and research-to-public-code boundaries | Retain |
| `rigorous-research-workflow` | Orchestrator | broad research workflow prompts | lifecycle transitions, upstream invalidation propagation, exact specialist delegation, and privacy-safe multi-artifact productization | Retain as thin composition layer, not a headline generalist |

## Why the Boundaries Matter

The suite would lose important failure coverage if these pairs were merged:

- scientific argument versus binary document structure;
- evidence discovery/verification versus reader-facing synthesis;
- general complex-genome study design versus imputation benchmark fairness;
- computational execution provenance versus cross-session workspace authority;
- specialist execution versus cross-stage invalidation and release gates.

Conversely, `rigorous-research-workflow` must not absorb specialist instructions. Its value appears when upstream invalidation, lifecycle state, frozen baselines, or release gates must be coordinated across linked artifacts; an ordinary two-Skill handoff does not require it.

## Public Pattern Check

The audit compared the suite's responsibilities with broad scientific Skill collections such as [`K-Dense-AI/scientific-agent-skills`](https://github.com/K-Dense-AI/scientific-agent-skills), official and community Skill collections cited in [PROVENANCE.md](PROVENANCE.md), document tooling such as [`flyfish-dev/word-ai`](https://github.com/flyfish-dev/word-ai), and public HPC/reproducibility Skill categories.

The check found substantial adjacent coverage for generic literature review, scientific writing, genomics, Word editing, and HPC guidance. It did not identify a direct one-for-one package for typed-authority workspace recovery, claim-to-full-text citation-delta closure, research-document submission baselines, or genotype-imputation benchmark contracts. Search coverage is necessarily incomplete and can become stale; differentiation therefore rests on inspectable contracts and tests, not on an absolute “only product” claim.

A local read-only check of the OpenAI curated Plugins Directory snapshot on 2026-08-20 also found `life-science-research`, which packages database-specific lookup Skills, and `ngs-analysis`, which packages executable assay and variant-calling pipelines. Those products are adjacent but solve different goals: this suite governs evidence, writing, delivery, reproducibility, complex-genome design, and imputation-benchmark validity rather than replacing database clients or assay pipelines. Catalog contents and availability can change, so this observation is a dated boundary check, not proof of exclusivity or future acceptance.

## Release Proof Required

A retention decision is not a quality certificate. Before publication, every Skill must still pass:

1. official package validation;
2. dependency-free suite and script regression tests;
3. clean-install direct, indirect, incomplete, boundary, composition, and negative activation tests;
4. synthetic task forward tests against its distinctive failure modes;
5. privacy, portability, provenance, license, and clean-history review.

Homepage language may call the four lead Skills “flagship” or “highly differentiated.” Avoid “unique,” “unreplaceable,” or “best” unless a documented, current comparison justifies that narrower claim.
