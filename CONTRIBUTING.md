# Contributing

Contributions should improve a recognizable research workflow, a tested trigger boundary, or a deterministic safety check. Open an issue before a large redesign so ownership and overlap can be discussed without duplicating another Skill.

## Development Requirements

- Python 3.10 or newer for the standard-library validation tools.
- A current Codex installation with the official `skill-creator`; Plugin changes also use the official `plugin-creator`.
- Synthetic, privacy-safe fixtures only. Do not contribute private data, unpublished prose, reviewer wording, personal paths, credentials, or copyrighted full texts.

Keep `SKILL.md` focused on shared decisions and route conditional detail to `references/`. Put deterministic repeated operations in `scripts/` and copy-ready output material in `assets/`. Preserve implicit invocation unless an explicit-only product is intentionally proposed.

Before opening a pull request, run the repository release-check runner, the official validator for every changed Skill, all affected unit tests, link and privacy checks, and realistic positive, negative, boundary, and composition prompts. State which semantic or visual behaviors still require human review.

Do not edit generated release or installed copies independently. Change the source Skill, validate it, and regenerate downstream packages.
