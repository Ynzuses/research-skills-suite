# Research Skills Suite

Research Skills Suite is a producer-oriented collection of Codex Skills for evidence-traceable research. It converts recurring research practice into reusable, privacy-safe workflows while keeping project facts, private data, and local infrastructure out of the public packages.

## Skills

| Product role | Skill | Distinct responsibility |
| --- | --- | --- |
| Flagship | `manage-workspace-memory` | Project-aware directory and authority design, three-hop recovery, event-driven maintenance, drift audit, frozen baselines, and resumable handoff |
| Flagship | `evidence-traceable-literature-review` | Reproducible discovery plus primary-full-text, claim-level evidence, contrary evidence, citation-delta, and source-package closure |
| Flagship | `research-document-delivery` | Word/Markdown/PDF authority, OpenXML safety, comment closure, cross-format parity, final-hash validation, and submitted baselines |
| Vertical flagship | `genotype-imputation-benchmarking` | Information-interface fairness, leakage-safe truth, evaluation universes, evaluability, calibration, downstream validation, and source-level ablations |
| Specialist | `scientific-writing-and-revision` | Scientific argument, purpose drift, epistemic status, feedback adjudication, document-wide repair, and short/long-form parity |
| Specialist | `genomics-study-design` | Reference- and species-aware genomics for non-model, polyploid, duplicated, and other complex genomes |
| Specialist | `reproducible-computational-research` | Local/HPC provenance, idempotent checkpoints, missing-versus-zero state, quantitative handoff, and public-code boundaries |
| Orchestrator | `rigorous-research-workflow` | Cross-stage state, invalidation propagation, specialist delegation, transition gates, and privacy-safe release decisions |

The suite deliberately does not split search from literature synthesis, manuscript drafting from language revision, HPC execution from computational provenance, or session startup from session closure. It does separate writing from binary document engineering, general genomics from genotype-imputation benchmarking, and workspace-memory architecture from research governance because those pairs have materially different inputs, failure modes, and completion checks.

All eight Skills are independently installable and have a defensible user goal. They are not marketed at the same level: the four flagship products carry the suite's strongest differentiation, the three specialists provide reusable depth, and `rigorous-research-workflow` is intentionally a thin composition layer rather than an all-purpose research Skill.

See [MARKET_POSITION.md](MARKET_POSITION.md) for the retention, overlap, and release-proof audit.

## Automatic Selection and Maintenance

Every Skill explicitly allows implicit invocation. Its frontmatter description—not the UI default prompt—is the primary automatic-selection interface. The golden specification therefore tests direct, indirect, incomplete, boundary, composition, and negative prompts for every Skill.

`manage-workspace-memory` can bootstrap or safely merge a project-level `AGENTS.md` contract that routes later matching tasks to the appropriate installed Skill and performs event-driven closure after durable changes. This is active-session automation: Skills are not background daemons, and implicit invocation does not authorize file moves, deletion, publication, cloud synchronization, or writes outside the current task.

## Deterministic Automation

The suite uses model judgment for scientific meaning and small dependency-free tools for repeatable structural checks:

| Check | Tool |
| --- | --- |
| Workspace routes, links, IDs, placeholders, status fields, and frozen-baseline signals | `manage-workspace-memory/scripts/audit_workspace_memory.py` |
| Search/screening/evidence/source-package closure | `evidence-traceable-literature-review/scripts/validate_review_bundle.py` |
| Scientific purpose, claims, feedback decisions, and surface mappings | `scientific-writing-and-revision/scripts/validate_revision_state.py` |
| DOCX ZIP/OpenXML structures and comment-family closure | `research-document-delivery/scripts/audit_docx_package.py` |
| Delivery membership, current hashes, frozen state, and validation binding | `research-document-delivery/scripts/verify_delivery_record.py` |
| Computational tasks, checkpoints, artifacts, and missing/zero/stale state | `reproducible-computational-research/scripts/validate_run_manifest.py` |
| Assembly/sample/split/QC/scale/hypothesis contract closure | `genomics-study-design/scripts/validate_study_contract.py` |
| Imputation interfaces, truth, leakage, metrics, conditions, and comparison coverage | `genotype-imputation-benchmarking/scripts/validate_benchmark_contract.py` |
| Cross-stage lifecycle authorities, transitions, and invalidations | `rigorous-research-workflow/scripts/validate_workflow_state.py` |
| Recorded clean-install activation precision, recall, exact routing, and behavior | `tests/score_activation_results.py` |

These tools are read-only unless their documentation explicitly says otherwise. A structural PASS is not evidence that a scientific claim, biological truth set, prose argument, or rendered layout is correct.

## Requirements

- A current Codex build with Skill support. Full-suite distribution uses the Plugin interface.
- Python 3.10 or newer to run the dependency-free validators and release tooling. The Skills themselves are instruction packages; Python is not required merely to read their guidance.
- The current official `skill-creator` for Skill validation and `plugin-creator` for a generated Plugin tree.

## Install, Update, and Remove

The public release layout is a Plugin containing all eight Skills. In the Codex app, install **Research Skills Suite** from the marketplace or Plugins Directory that carries the release. In the CLI, first list the configured marketplace names, then use the reported name in the remaining commands:

```text
codex plugin marketplace list
codex plugin add research-skills-suite --marketplace MARKETPLACE_NAME
codex plugin marketplace upgrade MARKETPLACE_NAME
codex plugin remove research-skills-suite --marketplace MARKETPLACE_NAME
```

For one Skill only, ask the installed `skill-installer` to install the corresponding `skills/<skill-name>` directory from the tagged repository release, or copy that complete Skill directory into the user's Codex Skills directory (`~/.codex/skills/` on Unix-like systems or `%USERPROFILE%\.codex\skills\` on Windows). Do not copy only `SKILL.md`; its `agents/`, `references/`, `scripts/`, and `assets/` may be part of the contract.

After installation or update, start a fresh Codex session so discovery metadata is reloaded. Installed copies are deployment artifacts: update the source or tagged release, validate it, then reinstall or redeploy instead of hand-editing the installed copy.

## Try It Without Naming a Skill

Implicit selection is enabled for every Skill. Representative requests include:

- “Inspect this new multi-deliverable project and propose the smallest recoverable workspace structure before creating anything.”
- “Continue this half-finished literature review from its search and screening records, then identify which claims still lack verified full text.”
- “Revise the argument and evidence strength across this report, its tables, conclusion, and short summary.”
- “Audit this genotype-imputation comparison for information-interface fairness, leakage, evaluability, and downstream validity.”

Automatic discovery is tested separately from package structure. A release claim requires recorded clean-session activation results; `allow_implicit_invocation: true` alone is not treated as behavioral proof.

## Source and Public Layouts

This development tree is intentionally flat: its eight immediate Skill directories are the authoritative editable source. The deterministic exporter creates the distributable layout with `.codex-plugin/plugin.json` at the root and the same eight directories under `skills/`. Both layouts are validated, but they must not coexist in one tree or become independent edit branches.

## Public Distribution

For a single Skill, a repository path can be installed directly. For the full suite, the intended public distribution is a Codex Plugin that bundles these skill directories and carries repository-level version, license, release notes, and installation metadata. The distributable Plugin manifest is stored in .codex-plugin/plugin.json.

Public support uses [GitHub Issues as described here](SUPPORT.md); security-sensitive reports use the repository's private advisory channel under [SECURITY.md](SECURITY.md). The package's data-handling boundary is documented in [PRIVACY.md](PRIVACY.md), and [TERMS.md](TERMS.md) distinguishes research assistance from scientific or regulatory proof. Final Plugin metadata must link to the public rendered versions of those policies.

Remote creation or publication is a separate maintainer action. Every public version must come from a clean export with an independent privacy scan, license audit, current hashes, and fresh validation.

## Product Principles

- One recognizable user goal per Skill; no micro-skill fragmentation.
- Trigger descriptions specify positive, negative, and composition boundaries.
- Main instructions stay concise; detailed knowledge lives one level under `references/`.
- Deterministic scripts are added only for repeated or fragile automation.
- Persisted contracts fail closed on unknown schema versions; migrations preserve the prior record, and project-specific fields use declared `extensions` objects instead of redefining portable meanings.
- Project names, local paths, private data, personal identities, and unpublished results do not enter reusable Skills.
- Scientific defaults are explicit, evidence is traceable, and uncertainty is preserved.
- Review revisions include citation-delta, epistemic-status, and short-summary parity checks rather than only local prose cleanup.
- Submitted documents become immutable baselines; later feedback starts a new, independently validated revision.
- Golden prompts cover direct, indirect, incomplete, boundary, composition, and non-trigger requests.

## Validation

See [TESTING.md](TESTING.md), `tests/validate_suite.py`, and `tests/golden-prompts.tsv`. Structural validation, privacy scanning, trigger review, and independent task forward tests are all release gates.

## Provenance

The methods are an original synthesis of recurring research practice. Platform structure follows current official Codex and Agent Skills specifications. Public repositories were studied for product patterns, not copied verbatim. See [PROVENANCE.md](PROVENANCE.md) and [NOTICE](NOTICE).

## Version

Suite version: `0.6.0`. See [CHANGELOG.md](CHANGELOG.md).
