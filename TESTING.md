# Testing Strategy

The dependency-free tooling requires Python 3.10 or newer. Run commands from the suite source root or from a generated public Plugin root; the validators detect the supported layout explicitly.

Run the dependency-free suite gate first:

```text
python tests/validate_suite.py
```

Then run the synthetic regression suite:

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

For a private-to-public export, repeat `--deny-term <term>` for project names, local workstream labels, people, datasets, and other identifiers known only to the source workspace. This deterministic gate complements, but does not replace, the official Skill and Plugin validators or independent forward tests.

## 1. Structural Validation

Run the current official `quick_validate.py` against every directory containing `SKILL.md`. On Windows, force UTF-8 for the validator process (for example with `PYTHONUTF8=1`) so the system code page does not create a false decode failure. Confirm frontmatter contains only `name` and `description`, names match directory names, descriptions are syntactically valid, and `agents/openai.yaml` exists and matches the Skill.

## 2. Metadata Tests

Use `tests/golden-prompts.tsv` as the target-aware activation specification. Each row records the Skill being tested, the complete expected and forbidden suite activations, the request class, and an observable behavioral contract. Every Skill must have:

- direct requests naming the task;
- indirect requests that describe the task without naming the Skill;
- incomplete requests where the Skill should establish a contract;
- boundary requests that must route to a neighboring capability while forbidding the target Skill;
- negative requests that should not trigger the Skill;
- composition requests that should invoke the exact required Skill set, including cross-stage orchestration only when warranted.

Descriptions are product metadata. A Skill that triggers on every adjacent task fails precision; a Skill that only triggers when named fails recall.

The golden TSV passing `validate_suite.py` proves coverage and schema only; it does not prove model activation. Run every prompt in a clean Plugin installation without naming the Skill, record model/date, actually loaded suite Skills, and behavioral review in a copy of `tests/activation-results.tsv.template`, then score it:

```text
python tests/score_activation_results.py \
  --results <activation-results.tsv> \
  --candidate-root <candidate> \
  --installed-root <clean-installed-copy> \
  --evidence-manifest <external-evidence-manifest.json>
```

The default gate requires a complete run, no unscored behavior, micro precision of at least 0.95, micro recall of at least 0.90, exact routing of at least 0.90, per-Skill precision of at least 0.95, per-Skill recall of at least 0.90, and per-class exact routing of at least 0.90. For a release candidate, also review every failure manually and run a strict `1.0` threshold pass when platform behavior makes that attainable; thresholds must never conceal a safety-relevant false positive or a flagship false negative.

## 3. Content and Link Checks

Verify every Markdown link resolves within the package, every referenced Skill name exists in the suite or is clearly external, and no unresolved placeholder remains outside intentional templates. Check that detailed references are only one level below each Skill. Compile every Python script without producing cache files and parse every JSON template; `validate_suite.py` performs these deterministic checks.

## 4. Privacy and Portability Scan

Scan tracked and untracked source files for:

- local drive paths, usernames, hostnames, and private URLs;
- project, paper, cohort, sample, collaborator, or supervisor identifiers;
- sample-level or reversible research data;
- secrets, tokens, credentials, and API keys;
- copied copyrighted passages;
- platform-specific assumptions presented as universal facts.

The source tree may mention public repository and specification names in provenance documentation; deployed Skill packages should contain only what is needed to perform their tasks.

## 5. Independent Forward Tests

Use fresh agents and realistic tasks. Provide the Skill path and the user-like task, not the expected answer, suspected bug, or prior diagnosis. Review whether the agent:

- establishes the correct contract;
- follows the domain workflow;
- recognizes stop conditions;
- composes with adjacent Skills appropriately;
- avoids project-specific assumptions;
- produces an inspectable result.

Forward tests should be read-only or use synthetic temporary artifacts unless the user explicitly authorizes live changes.

For every deterministic script, test valid, invalid, malformed, non-UTF-8, Chinese/space path, path-escape, stable-output, and no-mutation cases as applicable. A validator must distinguish structural failure from read/usage failure and must state what semantic or visual truth it cannot establish.

For workspace-memory tests, include both a clean bootstrap and a contradictory existing workspace. A passing result must distinguish physical state, current status, stable design, and history; repair stale routes without overwriting unrelated content; and enable a fresh agent to resume through progressive reading.

Also test a complex blank project with multiple deliverables, shared source assets, sensitive data, remote computation, and a frozen report; an unconventional but coherent existing directory; a durable event sequence; a no-change session whose memory hashes remain identical; and a read-only drift audit that reports but does not repair. Verify that an authorized bootstrap merges routing into the discoverable instruction entry rather than merely storing an unused template.

For comment-driven writing tests, include reviewer example rewrites that are helpful but not publication-ready and a reviewer question about a specialist term that is unnecessary at the marked location. A passing result must preserve the intended correction without copying the example mechanically, decide whether the term should be omitted, relocated, or defined, explain necessary terms only at their first functional use, establish the input-to-output computation before technical module lists, replace vague change predicates with concrete effects, remove answer-to-reviewer prose, and synchronize the clean Word and Markdown copies. If the task contract explicitly requires a method family or training component, the revised argument must retain that requirement while locating it on a concrete computation rather than demoting it to optional post-processing. Also test the inverse scope case: a method required in the overall project but assigned only a supporting role in the current review must remain visible without taking over the heading tree, tables, recommendations, or conclusion; its implementation choices should be routed to the named later deliverable. The agent must then delete repeated boundary disclaimers from intervening sections and tables, keeping only reader orientation and a genuine handoff, and must judge prominence from structure and space rather than from disclaimers. Add a second-pass case in which the supporting method has correct structural prominence but is still introduced through negative “this document does not...” language, literature synthesis sounds like a current-project result, and future diagnostics are declarative in a table. The passing response must introduce the method by positive scientific role, attribute the synthesis to existing literature, make unrun diagnostics conditional, and preserve the same comparator role across prose and tables.

Add an epistemic-status case in which a discussion-oriented review and its short group summary sound as though a technical route has already been approved. A passing result must classify source facts, review synthesis, conditional inference, approved decisions, and open options; preserve genuine evidence strength; and keep the conclusion, tables, abstract, and short summary at the same certainty as the body.

For citation-delta tests, delete, merge, and add synthetic review passages after an initially valid bibliography. A passing result must identify orphan sources, unsupported additions, claim-role mismatches, and citation inflation; verify the necessary primary full texts; and rebind first-appearance numbering, the reference list, the evidence matrix, the conclusion, and the source package.

For clean Word delivery tests, include a document whose visible comments are gone but `word/people.xml`, a people relationship, and a matching content-type declaration remain, plus edited paragraphs with citation superscripts, punctuation-specific font runs, and a math expression such as `r_j^2`. A passing result must remove the entire comment/people relationship closure without damaging unrelated parts and must preserve each relevant run-property role rather than reusing the first run style for the whole paragraph. Split one citation group during the edit so aggregate superscript counts change legitimately; the validator must distinguish citation runs from formula runs and confirm variable text, math font, italic state, and vertical alignment semantically.

Add a submitted-baseline case: the first artifact and its validation are already recorded as delivered, and a new comment arrives. A passing result must leave the submitted hash unchanged, create a new revision identity, retain the authority link, and rerun every check affected by the new copy instead of reusing the earlier render.

For public-release tests, provide private-style review incidents only as synthetic fixtures. A passing result must retain the generalized failure pattern, repair rule, and acceptance test while excluding names, paths, hashes, source identities, project decisions, reviewer wording, and unpublished conclusions.

## 6. Deployment Verification

After copying validated directories into the global Skills location:

1. compare relative file lists;
2. compare SHA-256 for every source and deployed file;
3. confirm a fresh Codex session discovers each Skill from the intended installation;
4. do not hand-edit deployed copies.
5. After any final status/index/audit-pointer edit, re-run the source-to-deployed hash comparison and the artifact hash-bound release check.

## 7. Release-Evidence Boundary

Keep four results distinct in release notes:

- package/schema validation;
- deterministic script regression tests;
- actual clean-install Skill activation results;
- task-level scientific or document forward tests.

Do not label the suite “fully tested” when only the first two pass. Record the model, product build, date, installation method, prompts, loaded Skills, behavioral adjudication, and known platform variance for activation evidence.

## 8. Trusted Release Gate

Never request a release verdict from `tests/run_release_checks.py` inside the candidate. Execute the runner from a separate trusted source root. Candidate and clean-installed trees, trusted source root, trust policy, official validators, activation results, and evidence manifest must occupy disjoint trust locations. The runner rejects links, reparse points, hard-linked files, case-colliding paths, nested roots, non-UTF-8 child output, and any candidate or trusted-input identity change during an executable stage.

First generate a pending policy without executing candidate code:

```text
python <trusted-source>/tests/run_release_checks.py \
  --root <candidate> --trusted-root <trusted-source> \
  --official-validator <external-quick_validate.py> \
  --plugin-validator <external-validate_plugin.py> \
  --activation-results <external-activation-results.tsv> \
  --installed-root <clean-installed-copy> \
  --evidence-manifest <external-evidence-manifest.json> \
  --write-trust-policy-draft <external-trust-policy.json>
```

Review every resolved path, file/tree digest, test-set inventory, evidence identity, and threshold. Only then change `status` to `approved` and fill a human `approver` plus an ISO timestamp with timezone. Do not approve the static `tests/RELEASE_TRUST_POLICY.json.template`; the generated policy is candidate-specific. Run the gate with the same six threshold values recorded in the policy:

```text
python <trusted-source>/tests/run_release_checks.py \
  --root <candidate> --trusted-root <trusted-source> \
  --official-validator <external-quick_validate.py> \
  --plugin-validator <external-validate_plugin.py> \
  --activation-results <external-activation-results.tsv> \
  --installed-root <clean-installed-copy> \
  --evidence-manifest <external-evidence-manifest.json> \
  --trust-policy <external-trust-policy.json> --release
```

The runner uses only the trusted static validator, scorer, golden prompts, and `test_*.py` set; trusted tests run on an isolated mirror with the candidate test layer replaced. Candidate-bundled checks remain useful self-tests but are not release evidence. Every child process is decoded as strict UTF-8, so malformed output fails instead of becoming mojibake or silently replacing bytes. When inspecting text from PowerShell 5.1, use `Get-Content -Encoding UTF8`; avoid relying on its legacy default code page. A passing result is a hash-bound technical gate only. The policy is an auditable approval record, not a cryptographic signature or publication authorization.
