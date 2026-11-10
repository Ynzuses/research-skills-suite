# v1.1.0 — Research Skills Suite

This minor release adds a fifth member for independent review and makes the literature-review member harder to fool with a single reader's blind spots. The four earlier members' validators and the review-bundle schema are unchanged.

## What changed

- **New member: `research-review-panel`.** Before a manuscript, literature review, analysis plan, statistical or method decision, scientific code, or figure is submitted, frozen, or acted on, several reviewers challenge it separately. They are made to differ (a different model family where the host offers one, otherwise different materials and lenses), and one of them argues that the artifact should not go forward. Every finding names a location. Disputes are settled by opening the cited passage, table, or script; the number of reviewers who agree, their confidence, and position changes without a stated reason do not count. Reviewers do not edit, and accepted repairs go to one writer and are reviewed again. A variant tests competing explanations for an unexpected result. Ships with panel-design and adjudication references, a reviewer brief, and a findings ledger template.
- **Independent screening passes.** `evidence-traceable-literature-review` can screen the same candidates in two or more passes that cannot see each other's decisions. Agreements stand. Records with any disagreement or low confidence are adjudicated against the criteria or the full text, not by counting passes. Per-pass decisions go in a companion table, so `screening-ledger.tsv` keeps its schema.
- **Independent verification pass.** Before a review is circulated, each material claim can be rechecked by a verifier that did not draft it and that receives the claim and the source, not the author's reasoning. Outcomes use the evidence ledger's existing direction and strength fields. A claim that could not be checked is never counted as supported, and a non-supporting outcome is confirmed at the source before the document is changed.
- **Optional reference-manager route.** A per-task rule decides whether a review passes through a reference library: use it when the sources themselves are a deliverable, the library will be shared, or the bibliography will change over several rounds; skip it for short result-only work. The ledgers and the hash-bound full-text package stay authoritative, the library is a mirror, only verified sources enter it, and a bibliography formatted from it is still checked.
- The two independence mechanisms prefer a reviewer from a different model family where the host offers one, and apply the workspace's privacy rule before task content leaves the machine.

## Install or update

```sh
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.1.0 --skill "*" --agent codex
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.1.0 --skill "*" --agent claude-code
```

Project scope is the default; choose a member with `--skill <name>`, add `--global` for user scope or `--copy` if links are unavailable. See [INSTALL.md](INSTALL.md) for prerequisites, destinations, dependencies, updates and removal. Migrating the old eight-member installation can require other groups; these commands install the five Research members only.

## Compatibility and validation

No existing member's runtime script, schema or CLI behavior changes, and existing review bundles validate as before. The suite's own validator, exporter and release checks now expect five members, and the regression suite was rerun on the source and on an independent candidate copy. The new member and the new passes describe methods and are not themselves measured here: this release does not claim a tested gain in review quality, screening recall or citation accuracy. See [STABILITY.md](STABILITY.md), [VALIDATION.md](VALIDATION.md) and [CHANGELOG.md](CHANGELOG.md).

## Downloads and support

Assets: `research-skills-suite-1.1.0.zip` and `research-skills-suite-1.1.0.zip.sha256`. Verify the ZIP's SHA-256 before extraction; it includes `SHA256SUMS` and `RELEASE_MANIFEST.json`. GitHub's automatic Source code archives have different packaging bytes.

Copyright 2026 Ynzuses. [Apache-2.0](LICENSE); retained terms in [NOTICE](NOTICE). See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md) for reproducible feedback and private security reporting.
