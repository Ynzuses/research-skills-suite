# v1.0.1 — Research Skills Suite

This documentation patch connects the legacy all-in-one release and the maintained groups into one navigable project history. The four Research members and their runtime interfaces are unchanged.

## Legacy-to-current navigation

- README links all six current product groups and their fixed releases.
- [MIGRATION.md](MIGRATION.md) maps all eight former v0.6.0 members to their maintained homes, with direct installation links and duplicate-installation guidance.
- Additional Git, Office, writing and resume members are distinguished from the original eight. Group installation and independent SemVer histories are retained.
- The [legacy v0.6.0 release](https://github.com/Ynzuses/research-skills-suite/releases/tag/v0.6.0) remains in this repository's history. A dated migration notice links its readers to the current groups; its original notes, tag, tree and source archives remain available.

## Install

```sh
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.0.1 --skill "*" --agent codex
```

Project scope is the default; choose a member with `--skill <name>`, add `--global` for user scope or `--copy` if links are unavailable. See [INSTALL.md](INSTALL.md) for prerequisites, destinations, dependencies, updates and removal. Migrating the old eight-member installation can require other groups; this command installs the four Research members only.

## Compatibility and validation

No member, runtime script, test, schema or CLI behavior changes. The documentation-only candidate is checked for exact bytes, frontmatter, language and links, and the fixed public tag is installed in an isolated project. Existing regression evidence applies to unchanged runtime files; this patch does not claim a new independent model or scientific validation. See [STABILITY.md](STABILITY.md), [VALIDATION.md](VALIDATION.md) and [CHANGELOG.md](CHANGELOG.md).

## Downloads and support

Assets: `research-skills-suite-1.0.1.zip` and `research-skills-suite-1.0.1.zip.sha256`. Verify the ZIP's SHA-256 before extraction; it includes `SHA256SUMS` and `RELEASE_MANIFEST.json`. GitHub's automatic Source code archives have different packaging bytes.

Copyright 2026 Ynzuses. [Apache-2.0](LICENSE); retained terms in [NOTICE](NOTICE). See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) for reproducible feedback and private security reporting.
