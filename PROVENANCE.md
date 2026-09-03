# Provenance and Design Sources

Normative platform sources were refreshed 2026-08-20. Public repository patterns were reviewed 2026-07-28 and spot-checked 2026-08-20.

## Normative Platform Sources

- OpenAI, “Build Skills”: <https://learn.chatgpt.com/docs/build-skills>
- OpenAI Developers, “Skills”: <https://developers.openai.com/plugins/concepts/skills>
- OpenAI Developers, “Build Skills”: <https://developers.openai.com/plugins/build/skills>
- OpenAI Developers, “Optimize metadata”: <https://developers.openai.com/plugins/guides/optimize-metadata>
- Agent Skills specification: <https://agentskills.io/specification>
- OpenAI Skills repository: <https://github.com/openai/skills>

The installed official `skill-creator` and `plugin-creator` are the operational authority for local scaffolding, frontmatter, interface metadata, validation, and plugin manifests. If these sources conflict with an external repository pattern, the current official local tooling wins.

## Public Repository Pattern Review

The following public repositories were inspected for general product patterns. The snapshot records were refreshed through the GitHub public API on 2026-08-20. `NOASSERTION` means the API did not return an SPDX identifier; it is not a claim that the repository has no license. Star counts and popularity labels are intentionally excluded because they are not design evidence.

| Repository and reviewed snapshot | API SPDX | Pattern considered |
| --- | --- | --- |
| [`openai/skills`](https://github.com/openai/skills), `49f948faa9258a0c61caceaf225e179651397431` | `NOASSERTION` | consistent Skill packaging and interface metadata |
| [`anthropics/skills`](https://github.com/anthropics/skills), `0a64e398ec6bb34a494f0c347e8ccae53a862f8e` | `NOASSERTION` | document collaboration and reader-oriented task staging |
| [`obra/superpowers`](https://github.com/obra/superpowers), `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` | `MIT` | phase boundaries and diagnostic discipline |
| [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills), `df1edb2e05487d0aa6d93c747141e0aed1187f25` | `MIT` | production-oriented categories and trigger descriptions |
| [`K-Dense-AI/scientific-agent-skills`](https://github.com/K-Dense-AI/scientific-agent-skills), `390f5146bf3c1877cf15636a3dd7b775e4f0f185` | `MIT` | broad scientific coverage and progressive references; the older `claude-scientific-skills` repository path redirects to this canonical repository |
| [`vercel-labs/agent-skills`](https://github.com/vercel-labs/agent-skills), `b8caa260a420a73042e35521de4b5c8baf6446cc` | `NOASSERTION` | compact specialist rules organized by impact |
| [`cline/cline`](https://github.com/cline/cline), `16875140fbc7bae51aad79c203837b4f51e54aa5` | `Apache-2.0` | separation of project brief, active context, progress, and related knowledge |
| [`RooCodeInc/Roo-Code`](https://github.com/RooCodeInc/Roo-Code), `b867ec9145750d0ae1ff7f02d35406e9bf2a0b16` | `Apache-2.0` | persistent workspace and mode patterns |
| [`github/spec-kit`](https://github.com/github/spec-kit), `ad057b586f654836e8c4aef7ec20b8dd45873dee` | `MIT` | stable constitutions, specifications, templates, and explicit gates |
| [`Fission-AI/OpenSpec`](https://github.com/Fission-AI/OpenSpec), `1ebddd17f40dde15dfd28289e4493c3cf05ee9df` | `MIT` | shared planning versus local execution and single ownership |
| [`agentsmd/agents.md`](https://github.com/agentsmd/agents.md), `d1ac7f063d20e70015ed6732664049ae4ba9d74e` | `MIT` | predictable repository-level agent instruction entries |
| [`mem0ai/mem0`](https://github.com/mem0ai/mem0), `ed38ddf8731fb7fab7c41bb0f8ab3185df23e7c5` | `Apache-2.0` | contrasting vector-memory runtime used to define the local-file non-goal |
| [`flyfish-dev/word-ai`](https://github.com/flyfish-dev/word-ai), `1edacba40e89073b0e03ec6dcf0fcc380dbcb33f` | `AGPL-3.0` | adjacent Word tooling considered only for market-boundary comparison |

Only abstract patterns were retained. No external Skill text, examples, assets, or code were copied into this suite, and no reviewed repository is a runtime or vendored dependency. The suite's Python helpers use the standard library only. External defaults that conflicted with the research workflow were not adopted. In particular, `manage-workspace-memory` uses three-hop progressive routing rather than requiring every memory file at every startup, and it does not send private workspace content to an external semantic-memory service by default.

The 2026-08-20 spot check also compared broad public scientific-Skill coverage with document tooling and genotype-imputation/HPC categories. It informed product boundaries and negative-trigger tests only; no search can prove global uniqueness. The release therefore describes inspectable differentiators and validation evidence rather than claiming absolute non-substitutability. See [MARKET_POSITION.md](MARKET_POSITION.md).

## Original Method Synthesis

The suite generalizes recurring lessons from research design, literature review, scientific writing, reviewer-comment adjudication, citation-delta auditing, Word/Markdown/PDF delivery, submission-baseline control, computational reproducibility, HPC execution, non-model genomics, duplicated-genome analysis, association studies, genotype-imputation benchmarking, and layered cross-session workspace management during a long-running research program.

Iteration follows a privacy-preserving abstraction rule: retain the failure pattern, general repair rule, and acceptance test; discard the local document text, reviewer identity, project path, artifact hash, source-package identity, and unpublished conclusion that revealed the problem. Public tests use synthetic prompts that reproduce the reasoning challenge without reproducing the private incident.

The workspace-memory method originated from repeated use of rule entry points, long-term indexes, current status panels, stable designs, asset indexes, topic memories, dependency graphs, Git history, and closed audit archives. Its distinctive contribution is typed authority plus progressive reading: rules and the long-term index route to current status, which then routes to only the task-relevant design, asset, topic, or primary evidence.

Source incidents were used only to identify transferable rules. The reusable Skills exclude project names, organism-specific findings presented as universal facts, sample counts, private cohorts, local paths, usernames, hostnames, supervisor wording, unpublished results, and copied thesis text.

## Update Rule

When official specifications or source practices change:

1. document the new source and access date;
2. distinguish normative requirements from optional patterns;
3. update source Skills first;
4. rerun structural, metadata, trigger, privacy, and forward tests;
5. redeploy and compare hashes;
6. record the change in the suite changelog.
