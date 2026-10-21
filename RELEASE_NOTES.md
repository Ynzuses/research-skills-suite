# v1.0.0 — Research Skills Suite

Traceable literature evidence, scientific arguments, reproducible computation and coordinated research revisions across disciplines.

This is the group's first stable release. For researchers who need traceable literature evidence, evidence-calibrated scientific arguments, reproducible computation, or coordinated revisions across linked research outputs. Select a specialist for an ordinary single task; use lifecycle coordination when several artifacts must move together.

## Included in this release

- `evidence-traceable-literature-review`
- `scientific-writing-and-revision`
- `reproducible-computational-research`
- `rigorous-research-workflow`

Install members by task; other groups are optional companions. Bundled validators use Python 3.10+ and the standard library. Live search, full-text access, statistical computation, HPC scheduling, and document rendering require separately available tools. Loading these workflows does not require installing another group.

## Installation

```sh
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.0.0 --skill "*" --agent codex
```

Project scope is the default. Add `--global` for user-wide use or select one member with `--skill <skill-name>`. Check Node/npm/Git and existing installations first. See the [installation guide](INSTALL.md) for complete setup, dependencies, and removal.

## Migration

Read [MIGRATION.md](MIGRATION.md) before upgrading. Existing tags and versions retain their identities. Upgrading does not automatically remove old installations, install companion groups, or migrate local settings. `1.0.0` marks the first stable contract; internal review rounds are not public version numbers.

## Validation and limits

Contract checks do not establish scientific validity, evidence strength, or successful reproduction. Verify each research result against its actual inputs and final artifacts. See [VALIDATION.md](VALIDATION.md) for applicable structural, script, and entrypoint checks. Static checks do not guarantee future agent invocation, native application acceptance, or an external connection.

## Downloads and checksums

Custom assets: `research-skills-suite-1.0.0.zip` and `research-skills-suite-1.0.0.zip.sha256`. The extracted ZIP contains per-file `SHA256SUMS` and `RELEASE_MANIFEST.json`. GitHub's automatic Source code archives come from the tagged tree and have different packaging bytes and generated inventories.

Use `Get-FileHash <zip-path> -Algorithm SHA256` on Windows, `shasum -a 256 <zip-path>` on macOS, or `sha256sum <zip-path>` on Linux, then compare the companion checksum. Signatures, platform listings, and native application acceptance are reported only when actually completed.

Copyright 2026 Ynzuses. [Apache-2.0](LICENSE). See [NOTICE](NOTICE) for retained terms.

## Feedback and contributions

Use GitHub Issues for synthetic reproductions and installation feedback. See [CONTRIBUTING.md](CONTRIBUTING.md) for changes and validation expectations.
