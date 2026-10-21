# From the legacy suite to current groups

## One project history, maintained groups by purpose

[Research Skills Suite v0.6.0](https://github.com/Ynzuses/research-skills-suite/releases/tag/v0.6.0) is the legacy all-in-one release in this same repository. The maintained Research group continues that history. Domain-specific and general project/document methods have moved to purpose-based groups so users can install the work they need.

Every former member is accounted for below. Skill IDs are preserved; install their current owning group rather than assuming the four-member Research package still contains all eight. The original v0.6.0 tag, tree, source archives and original release notes remain available. A dated migration notice on its release page directs readers here.

## Every v0.6.0 member's current home

| Skill in v0.6.0 | Maintained group | Installation guide |
| --- | --- | --- |
| [`evidence-traceable-literature-review`](https://github.com/Ynzuses/research-skills-suite/blob/v1.0.1/evidence-traceable-literature-review/SKILL.md) | [research-skills-suite](https://github.com/Ynzuses/research-skills-suite) | [Install v1.0.1](https://github.com/Ynzuses/research-skills-suite/blob/v1.0.1/INSTALL.md) |
| [`scientific-writing-and-revision`](https://github.com/Ynzuses/research-skills-suite/blob/v1.0.1/scientific-writing-and-revision/SKILL.md) | [research-skills-suite](https://github.com/Ynzuses/research-skills-suite) | [Install v1.0.1](https://github.com/Ynzuses/research-skills-suite/blob/v1.0.1/INSTALL.md) |
| [`reproducible-computational-research`](https://github.com/Ynzuses/research-skills-suite/blob/v1.0.1/reproducible-computational-research/SKILL.md) | [research-skills-suite](https://github.com/Ynzuses/research-skills-suite) | [Install v1.0.1](https://github.com/Ynzuses/research-skills-suite/blob/v1.0.1/INSTALL.md) |
| [`rigorous-research-workflow`](https://github.com/Ynzuses/research-skills-suite/blob/v1.0.1/rigorous-research-workflow/SKILL.md) | [research-skills-suite](https://github.com/Ynzuses/research-skills-suite) | [Install v1.0.1](https://github.com/Ynzuses/research-skills-suite/blob/v1.0.1/INSTALL.md) |
| [`genomics-study-design`](https://github.com/Ynzuses/genomics-skills-suite/blob/v1.0.0/genomics-study-design/SKILL.md) | [genomics-skills-suite](https://github.com/Ynzuses/genomics-skills-suite) | [Install v1.0.0](https://github.com/Ynzuses/genomics-skills-suite/blob/v1.0.0/INSTALL.md) |
| [`genotype-imputation-benchmarking`](https://github.com/Ynzuses/genomics-skills-suite/blob/v1.0.0/genotype-imputation-benchmarking/SKILL.md) | [genomics-skills-suite](https://github.com/Ynzuses/genomics-skills-suite) | [Install v1.0.0](https://github.com/Ynzuses/genomics-skills-suite/blob/v1.0.0/INSTALL.md) |
| [`manage-workspace-memory`](https://github.com/Ynzuses/workspace-skills-suite/blob/v1.0.1/manage-workspace-memory/SKILL.md) | [workspace-skills-suite](https://github.com/Ynzuses/workspace-skills-suite) | [Install v1.0.1](https://github.com/Ynzuses/workspace-skills-suite/blob/v1.0.1/INSTALL.md) |
| [`research-document-delivery`](https://github.com/Ynzuses/office-authoring-suite/blob/v1.0.0/research-document-delivery/SKILL.md) | [office-authoring-suite](https://github.com/Ynzuses/office-authoring-suite) | [Install v1.0.0](https://github.com/Ynzuses/office-authoring-suite/blob/v1.0.0/INSTALL.md) |

## All current groups

| Group | Use it for | Skills | Current release |
| --- | --- | ---: | --- |
| [Research](https://github.com/Ynzuses/research-skills-suite) | Literature evidence, scientific writing, reproducible computation and research coordination | 4 | [v1.0.1](https://github.com/Ynzuses/research-skills-suite/releases/tag/v1.0.1) |
| [Genomics](https://github.com/Ynzuses/genomics-skills-suite) | Genomics study design and genotype-imputation benchmarking | 2 | [v1.0.0](https://github.com/Ynzuses/genomics-skills-suite/releases/tag/v1.0.0) |
| [Workspace and Git](https://github.com/Ynzuses/workspace-skills-suite) | Project memory, authority, handoffs and consent-based Git closeout | 2 | [v1.0.1](https://github.com/Ynzuses/workspace-skills-suite/releases/tag/v1.0.1) |
| [Documents and Office](https://github.com/Ynzuses/office-authoring-suite) | Word, PowerPoint, Excel and preservation-sensitive document delivery | 4 | [v1.0.0](https://github.com/Ynzuses/office-authoring-suite/releases/tag/v1.0.0) |
| [Voice-preserving writing](https://github.com/Ynzuses/voice-preserving-writing) | Drafting, revision and translation grounded in the writer's own material | 1 | [v1.0.0](https://github.com/Ynzuses/voice-preserving-writing/releases/tag/v1.0.0) |
| [Resumes and CVs](https://github.com/Ynzuses/targeted-resume) | Evidence-based company applications and academic CVs | 1 | [v1.0.0](https://github.com/Ynzuses/targeted-resume/releases/tag/v1.0.0) |

The six groups belong to one maintained family and retain separate installation and version histories. `voice-preserving-writing` and `targeted-resume` are additional groups, not renamed v0.6.0 members. `git-workspace-closeout`, `word-authoring`, `powerpoint-authoring` and `excel-authoring` are also additions to the former eight-member package.

## Upgrade an existing installation

1. Inventory the active Skill and plugin discovery roots in your agent, including project, user-wide, manual and legacy installs. Preserve local edits and a recoverable copy outside discovery.
2. Select the successor groups using the table. Read each linked installation guide for its fixed tag, prerequisites and real dependencies. Office's PowerPoint helper needs its same-group Word sibling.
3. Replace complete member directories once. Remove or disable an older duplicate only after confirming the replacement; do not leave the same Skill ID active from both the old bundle/plugin and a new group. Installing a group does not automatically uninstall an older plugin.
4. Verify discovery and an actual invocation in the target agent. Installation copies files; it does not migrate project state, configure Git preferences, grant client permissions or start a background service.

For example, install the current general Research group into the current project:

```sh
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.0.1 --skill "*" --agent codex
```

This installs its four members. Use the other groups' linked guides for the members that moved. Do not add all six groups solely to reproduce the legacy membership.

## Version and provenance boundaries

Each group's first stable release is v1.0.0, followed by independent SemVer updates. Research v1.0.1 adds this navigation; Workspace v1.0.1 clarifies Git onboarding and permissions. Old tags and package bytes are not relabeled or overwritten. Local 0.7-0.9 development iterations retain their historical identities and are not new published stable releases.

`research-document-delivery` keeps its historical ID and includes professional and academic rich documents. Scientific evidence methods remain topic-dependent. The two teaching/learning methods are not bundled, and third-party Skills retain their own distribution and licenses.
