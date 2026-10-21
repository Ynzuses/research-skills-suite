# Research Skills Suite: installation and deployment

This guide uses the Vercel `skills` CLI behind [skills.sh](https://skills.sh/docs/cli). Commands pin the installer to `skills@1.7.4`; the product tag is `v1.0.1`. These are independent versions. The tagged repository and release ZIP are alternative installation sources.

Upgrading from the former all-in-one v0.6.0 release? Read the [member-to-group migration map](MIGRATION.md) first; the current Research group contains four members.

## 1. Prepare the environment and inspect existing installations

CLI 1.7.4 requires **Node.js 22.20.0 or later** and npm/npx. For Git-source installs, prepare Git and access to the source host. Check:

```sh
node --version
npm --version
git --version
npx skills@1.7.4 list --agent codex
npx skills@1.7.4 list --agent codex --global
```

The first npx run may ask to download the CLI. Inspect existing Skills with the same names, including manual, plugin, and legacy-directory installations. Preserve local changes before replacing an entry. The CLI defaults to project scope; run it from the intended project root.

## 2. Inspect members, then install

```sh
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.0.1 --list
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.0.1 --skill "*" --agent codex
```

Expect **4** members: `evidence-traceable-literature-review`, `scientific-writing-and-revision`, `reproducible-computational-research`, `rigorous-research-workflow`. `--skill "*"` selects this group's members. Avoid `--all` here because it also selects all agents. Review the destination and installation method in the interactive prompts.

To select one member or install the group for your user account:

```sh
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.0.1 --skill evidence-traceable-literature-review --agent codex
npx skills@1.7.4 add https://github.com/Ynzuses/research-skills-suite/tree/v1.0.1 --skill "*" --agent codex --global
```

`--global` makes the installation available across projects; omitting it selects the current project. Keep double quotes around the star in PowerShell and common Unix shells. `/tree/v1.0.1` selects the Git tag. Do not append `@1.0.1` to a repository shorthand to mean a product version: the CLI also uses `@` to select a Skill.

## 3. Choose an agent and installation method

| Target | Option | Project directory | User directory |
| --- | --- | --- | --- |
| Codex | `--agent codex` | `.agents/skills/` | `~/.agents/skills/` |
| Claude Code | `--agent claude-code` | `.claude/skills/` | `~/.claude/skills/` |

See the [supported-agent list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md) for other targets. Discovery roots can differ with host versions, plugins, or legacy installations; a directory in this table is not proof that a particular client loaded it.

The CLI supports symbolic links and copies. Add `--copy` when links are unavailable, including on restricted Windows setups. Copying Skill files does not itself require Full access. After reviewing the intended installation, `--yes` can skip installer prompts; it does not authorize Git commits, account connections, or publication. Keep each complete Skill directory, including its supporting files.

## 4. Use a release ZIP or local checkout

Download `research-skills-suite-1.0.1.zip`, verify it against the companion `.sha256` file, and extract it. A complete checkout of the fixed tag also works. Install the member directories rather than treating the whole repository as one Skill. Replace this example with the actual extracted group directory:

```sh
npx skills@1.7.4 add "./research-skills-suite" --list
npx skills@1.7.4 add "./research-skills-suite" --skill "*" --agent codex --copy
```

Run from the target project root and use the correct relative or absolute source path. This avoids fetching the product repository, but obtaining the CLI through npm can still require a network connection. For fully offline use, prepare a trusted CLI cache in advance or manually copy complete member directories to the host's verified discovery root.

The custom asset contains `SHA256SUMS` and `RELEASE_MANIFEST.json`. GitHub's automatically generated Source code archives reflect the tagged tree and do not promise to include these packaging-generated files.

## 5. Prepare runtime dependencies

Bundled validators use Python 3.10+ and the standard library. Live search, full-text access, statistical computation, HPC scheduling, and document rendering require separately available tools. Loading these workflows does not require installing another group.

The CLI installs member directories. It does not run pip, install Office, connect accounts, or copy group-root support kits. Retain the full checkout or extracted group when using root-level requirements files and test kits. Select execution tools from the actual task environment.

## 6. Verify discovery and invocation

```sh
npx skills@1.7.4 list --agent codex
```

Add `--global` for a user-wide installation. Then inspect the target agent's available Skills and explicitly invoke `$evidence-traceable-literature-review` for a small task without external side effects. Confirm that the agent read the expected `SKILL.md`. Codex detects Skill changes; refresh or restart according to the host's instructions if an entry does not appear. Installer output does not prove agent discovery or correct workflow behavior.

If an entry is missing, inspect scope, working directory, agent selection, complete files, and duplicate legacy entries. Review project-level `.agents/skills` changes before sharing them. Keep personal runtime directories and credentials out of public repositories.

## 7. Update, roll back, or remove

```sh
npx skills@1.7.4 check
npx skills@1.7.4 remove evidence-traceable-literature-review --agent codex
```

Add `--global` when removing a user-wide installation. Remove only the intended member. `check` inspects upstream state; it does not establish compatibility. For a pinned tag, review the new release, then explicitly run `add` against its new `/tree/vX.Y.Z` URL using the same scope. Retain the previous ZIP, lock file, and local changes for rollback. Branch-tracking users can review and run `npx skills@1.7.4 update <skill-name> --project` or `--global`; automatic updates are not a version pin.

## Privacy, license, and help

The CLI is a separate third-party tool. Its [troubleshooting and telemetry documentation](https://github.com/vercel-labs/skills/blob/main/docs/troubleshooting.md) describes `DISABLE_TELEMETRY=1` and `DO_NOT_TRACK=1`; choose according to your environment. These settings do not make npm or Git downloads offline.

This group uses [Apache-2.0](LICENSE), with retained terms in [NOTICE](NOTICE) and [PROVENANCE.md](PROVENANCE.md). Commands follow the [Vercel CLI documentation](https://github.com/vercel-labs/skills/blob/main/docs/commands.md), checked on 2026-10-20. See [README.md](README.md) for scope and examples.
