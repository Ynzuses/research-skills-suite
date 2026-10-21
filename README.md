# Research Skills Suite

Traceable literature evidence, scientific arguments, reproducible computation and coordinated research revisions across disciplines.

For researchers who need traceable literature evidence, evidence-calibrated scientific arguments, reproducible computation, or coordinated revisions across linked research outputs. Select a specialist for an ordinary single task; use lifecycle coordination when several artifacts must move together.

Suite version: `1.0.1`.

## Project history and current groups

The former all-in-one [v0.6.0 release](https://github.com/Ynzuses/research-skills-suite/releases/tag/v0.6.0) is an earlier version of this project in this same repository's history. Its eight Skills now have four successor groups; the wider family also includes additional writing, Office, Git and resume methods.

| Group | Use it for | Skills | Current release |
| --- | --- | ---: | --- |
| [Research](https://github.com/Ynzuses/research-skills-suite) | Literature evidence, scientific writing, reproducible computation and research coordination | 4 | [v1.0.1](https://github.com/Ynzuses/research-skills-suite/releases/tag/v1.0.1) |
| [Genomics](https://github.com/Ynzuses/genomics-skills-suite) | Genomics study design and genotype-imputation benchmarking | 2 | [v1.0.0](https://github.com/Ynzuses/genomics-skills-suite/releases/tag/v1.0.0) |
| [Workspace and Git](https://github.com/Ynzuses/workspace-skills-suite) | Project memory, authority, handoffs and consent-based Git closeout | 2 | [v1.0.1](https://github.com/Ynzuses/workspace-skills-suite/releases/tag/v1.0.1) |
| [Documents and Office](https://github.com/Ynzuses/office-authoring-suite) | Word, PowerPoint, Excel and preservation-sensitive document delivery | 4 | [v1.0.0](https://github.com/Ynzuses/office-authoring-suite/releases/tag/v1.0.0) |
| [Voice-preserving writing](https://github.com/Ynzuses/voice-preserving-writing) | Drafting, revision and translation grounded in the writer's own material | 1 | [v1.0.0](https://github.com/Ynzuses/voice-preserving-writing/releases/tag/v1.0.0) |
| [Resumes and CVs](https://github.com/Ynzuses/targeted-resume) | Evidence-based company applications and academic CVs | 1 | [v1.0.0](https://github.com/Ynzuses/targeted-resume/releases/tag/v1.0.0) |

Choose groups by task. This repository installs the four Research members below; the table is navigation across the family, not a combined installation. See [MIGRATION.md](MIGRATION.md) for every former v0.6.0 member's current home, pinned installation links and the additional groups. The legacy tag and downloadable source remain available for reproducibility.

## Included Skills

| Skill | Purpose |
| --- | --- |
| [evidence-traceable-literature-review](evidence-traceable-literature-review/SKILL.md) | Reproducible search and screening, primary-source verification, contrary evidence and claim-level citation closure. |
| [scientific-writing-and-revision](scientific-writing-and-revision/SKILL.md) | Scientific reasoning, evidence-calibrated claims, feedback adjudication and consistency across long and short forms. |
| [reproducible-computational-research](reproducible-computational-research/SKILL.md) | Local/HPC provenance, environments, checkpoints, reruns and explicit missing, failed and verified-zero states. |
| [rigorous-research-workflow](rigorous-research-workflow/SKILL.md) | Coordinate upstream invalidation and lifecycle transitions across linked research artifacts; ordinary single tasks use their specialists. |

## Install with skills.sh

Run this from the project where you want to use the group:

```sh
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.0.1 --skill "*" --agent codex
```

This selects every member for Codex and defaults to the current project. Add `--list` to inspect available members or `--global` for user-wide installation. Use `--skill <skill-name>` to select one member, or choose another supported target such as `--agent claude-code`. Keep the first installation interactive so you can review its destination. Use `--copy` if symbolic links are unavailable.

See **[INSTALL.md](INSTALL.md)** for prerequisites, pinned versions, individual installation, discovery paths, dependencies, updates, and removal. Verify discovery and an actual invocation in the target agent after installing the files.

## Example requests

> Use $evidence-traceable-literature-review to build a reproducible search, screening record, and claim-to-source matrix for my research question, including contrary evidence.

> Use $reproducible-computational-research to audit this workflow's environment, input provenance, checkpoints, and missing or failed results.

These are requests to an agent. Codex supports explicit `$skill-name` invocation; other agents use their own invocation interface.

## Requirements and scope

Bundled validators use Python 3.10+ and the standard library. Live search, full-text access, statistical computation, HPC scheduling, and document rendering require separately available tools. Loading these workflows does not require installing another group.

Contract checks do not establish scientific validity, evidence strength, or successful reproduction. Verify each research result against its actual inputs and final artifacts.

## Versions, support, and license

`1.0.0` is this group's first stable contract. Read [MIGRATION.md](MIGRATION.md) before replacing an older installation and [RELEASE_NOTES.md](RELEASE_NOTES.md) for this release. Compatibility and verification limits are documented in [STABILITY.md](STABILITY.md) and [VALIDATION.md](VALIDATION.md).

The family navigation above links each group's maintained repository and release. When reporting a problem, include agent/CLI versions, reproducible steps, errors, and a synthetic example. Remove credentials, personal data, and unpublished material.

Copyright 2026 Ynzuses. [Apache-2.0](LICENSE). See [NOTICE](NOTICE) and [PROVENANCE.md](PROVENANCE.md) for attribution and retained component terms.

For proposed changes and reproducible reports, see [CONTRIBUTING.md](CONTRIBUTING.md).
