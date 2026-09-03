# Public Release and Privacy

Use this reference when converting local research experience into reusable methods, examples, skills, repositories, templates, or public documentation.

## Design for Consumers

A reusable research workflow is a product interface. Define:

- the users and tasks it serves;
- explicit triggers and non-triggers;
- required inputs and expected outputs;
- dependencies and composition with other tools or skills;
- failure modes and stopping conditions;
- validation evidence;
- versioning and maintenance ownership.

Prefer a small stable core with modular references over one monolithic instruction file. Keep domain-specific facts outside the reusable core unless the package is explicitly domain-specific.

## Separate Knowledge Layers

Classify source material before inclusion:

1. **General method:** transferable reasoning, workflow, or quality rule; eligible for the public package.
2. **Domain method:** reusable within a scientific field; include only when the scope and assumptions are explicit.
3. **Project decision:** local parameter, path, dataset, collaborator preference, or current status; keep in project memory.
4. **Sensitive fact:** personal, private, unpublished, contractual, or reversible information; exclude from public artifacts.

Generalize the lesson rather than copying the incident. For example, publish “verify actual rendered pagination after editing,” not the filename, page count, or reviewer identity from the project that produced the lesson.

When productizing review experience, separate four layers before writing reusable instructions: the observed failure pattern, the general repair rule, the acceptance test, and the local incident that must be discarded. Keep the first three; exclude project-specific wording, reviewer examples, hashes, bibliography identities, submission messages, and unpublished scientific conclusions. Replace any necessary example with a synthetic one that tests the same reasoning failure.

## Protect Privacy and Security

Public packages and examples must not contain:

- personal names, identifiers, sample IDs, or private cohort details;
- unpublished individual-level or reversible aggregate data;
- absolute local paths, usernames, hostnames, or storage layouts;
- API keys, credentials, tokens, private URLs, or hidden configuration;
- proprietary text, reviewer correspondence, or copyrighted source passages;
- logs or fixtures copied from sensitive work.

Use small synthetic examples. Scan both tracked and untracked files, metadata, history, notebooks, generated outputs, and test fixtures before release.

## Preserve Intellectual and Evidence Integrity

Document which parts are original synthesis, which are adapted from public standards, and which require attribution. Do not reproduce substantial copyrighted wording from papers, theses, reviewer comments, or external skills. Cite public standards where their specific framework is retained.

The research-method content in this skill is an original synthesis of recurring research-design, evidence, writing, review, and delivery practices. Its platform structure follows current Codex Skill conventions and should be checked against the official `skill-creator` before each release. It intentionally excludes project-specific scientific claims, private data, verbatim supervisor feedback, and local infrastructure details. A public repository should maintain a source and license inventory for any externally derived standards, assets, or code.

Choose a repository-level license before public release and verify that bundled code, templates, examples, fonts, images, and dependencies permit that license. A license for the repository does not override third-party terms.

## Package a Skill for Reuse

Use the current official `skill-creator` for platform-specific naming, frontmatter, metadata, directory, and validation requirements; this reference is not a substitute for that specification. This workflow adds research-specific release gates: include only transferable methods, use synthetic examples, disclose knowledge and license provenance, test composition with adjacent skills, scan for sensitive research content, and forward-test both trigger and non-trigger requests.

Design one skill around one recognizable user goal, but do not fragment a coherent workflow into tiny steps that always travel together. Keep `SKILL.md` concise and move detailed rules into references one level below it. Add deterministic scripts only when repeated automation or a fragile sequence justifies them.

Treat the description as product metadata. Put the core trigger terms early, state positive and negative boundaries, and maintain a golden prompt set covering direct, indirect, incomplete, boundary, composition, and non-trigger requests. Optimize for both recall and precision; an always-triggering skill is not well designed.

When several skills are intended to install and update as one public product, package them as a Codex Plugin for distribution while preserving individually valid skill directories for direct development and testing. Maintain plugin metadata, release notes, versioning, and installation documentation at repository level rather than copying them into every skill.

The active skill catalog consumes prompt context. Keep the suite small enough that descriptions remain visible and distinct; merge overlapping skills unless their inputs, failure modes, and completion standards materially differ.

## Public-Release Checklist

- Name and description are generic and accurately trigger the package.
- Main instructions are concise; detailed references are one level deep.
- No project name, organism, paper number, local path, private datum, or reviewer identity remains.
- No secret, credential, private endpoint, or identifying metadata remains.
- Examples are synthetic and do not reproduce unpublished results.
- Release tests reproduce generalized failure modes without embedding real review text, document hashes, source packages, or project decisions.
- External concepts and assets have compatible attribution and licenses.
- Structure validation passes in a clean environment.
- Trigger, non-trigger, and composition tests have been run.
- Direct, indirect, incomplete, boundary, and negative prompts exist in the golden test set.
- Instructions do not contradict platform safety or user authorization boundaries.
- A version, license, release note strategy, plugin or direct-install distribution path, and maintenance owner are chosen at repository level before publication.

## Change Discipline

Treat the version in the public source repository as authoritative. Deploy generated or copied installations from that source and verify their hashes. Make changes in the source package, validate them, then redeploy. Do not hand-edit the installed copy and allow it to drift from the publishable source.
