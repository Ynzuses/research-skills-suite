# Stable group provenance

Maintainer and distribution copyright holder: Ynzuses. License: Apache-2.0, with retained component notices. This 1.0.0 group is an ownership and distribution refactor of maintained methods. It does not adopt third-party Skills as original work or ship private documents, full texts, applicant profiles, machine inventories or development Git history.

Member set: `evidence-traceable-literature-review`, `scientific-writing-and-revision`, `reproducible-computational-research`, `rigorous-research-workflow`, and, since 1.1.0, `research-review-panel` (its design sources are listed in [Research review panel sources](#research-review-panel-sources)). Broader subject lists in the historical provenance below describe earlier method development and reviews, not additional bundled members or runtime dependencies. Original component notices and applicable terms are retained. No new upstream license or market comparison was performed as part of grouping.

## Pre-stable provenance record

# Provenance and Design Sources

Normative platform sources were refreshed 2026-08-20. Public repository patterns were reviewed 2026-07-28 and spot-checked 2026-08-20.

## Normative Platform Sources

The capability-routing iteration checked the official Skills, MCP, and workspace-instruction documentation on 2026-10-20: [Build skills](https://learn.chatgpt.com/docs/build-skills), [MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli), and [AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md). Progressive metadata/instruction loading and advertised connection/policy boundaries inform the workflow. Work-boundary rechecks and compact capability handoffs are suite design choices, not claims that the platform guarantees recall or enables every installed tool.

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

## Research review panel sources

`research-review-panel` joined the group in 1.1.0. It generalizes a maintainer practice of sending research documents, analysis decisions, and code to separate reviewers and settling their findings against sources, data, and scripts. Incidents that motivated it were used only to identify transferable rules; no project text, data, reviewer identity, or result is included.

The following public sources informed design choices and were checked on 2026-11-11. No text, prompt, or code was copied.

- Du et al., "Improving Factuality and Reasoning in Language Models through Multiagent Debate" (arXiv:2305.14325, 2023): the multi-agent debate setup that this Skill deliberately narrows.
- Choi, Zhu and Li, "Debate or Vote: Which Yields Better Decisions in Multi-Agent Large Language Models?" (arXiv:2508.17536): majority voting accounts for most of the gain usually credited to debate. This is why exchange between reviewers is optional and bounded.
- He et al., "Minority Sentinel: When to Overturn Majority Voting in Multi-Agent LLM Debates" (arXiv:2606.29270): because models make correlated errors, majority voting often overrides a correct minority answer. This is why findings are never settled by counting.
- Bertalanič and Fortuna, "The Cost of Consensus: Isolated Self-Correction Prevails Over Unguided Homogeneous Multi-Agent Debate" (arXiv:2605.00914): identical agents debating without assigned roles gained no accuracy over agents correcting themselves alone, at two to three times the token cost. This is why reviewers must differ and receive distinct lenses.
- Hao et al., "Not All Flips Are Conformity: Decomposing Stance Convergence in Multi-Agent LLM Debate" (arXiv:2606.00820): adopting a peer's answer can fix an error, introduce one, or swap one wrong answer for another, so convergence is not evidence of improvement. This is why a change of position needs a cited reason.
- Swanson et al., "The Virtual Lab of AI agents designs new SARS-CoV-2 nanobodies", Nature (2025): a dedicated critic role alongside specialist agents. This informed the standing opposing reviewer.
- Claude Code documentation, "Orchestrate teams of Claude Code sessions" (<https://code.claude.com/docs/en/agent-teams>): the competing-hypotheses pattern in which investigators try to disprove each other's theories.
- LeadDev, "Your AI-coding agents might need an org chart" (2026-08-04): in a reported writer-reviewer test on coding tasks, one model's pass rate fell after another model reviewed its output while the reverse pairing improved. This is why reviews from another model are adjudicated finding by finding.

Two public Skills were compared through their public listings on 2026-11-10; only abstract patterns were considered, neither is a dependency, and neither stated a license on the pages reviewed. `agent-review-panel` (wan-huiyan) uses an independent pass, bounded debate rounds, an alert when position changes lack new evidence, and counts agreement resting on one source as one observation; it requires one model for every reviewer and targets code and plans, whereas this Skill puts model diversity first and targets research artifacts. `academic-paper-reviewer` (Imbad0202) uses reviewer roles with a fixed opposing seat and typed evidence anchors, for manuscripts only.

No evaluation of this Skill's effect on review quality has been run. The cited studies concern question answering and coding benchmarks, not research review; they motivate the rules and do not validate them here.
