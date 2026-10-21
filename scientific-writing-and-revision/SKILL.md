---
name: scientific-writing-and-revision
description: "Draft or revise evidence-calibrated scientific arguments. Use for manuscripts, reviews, abstracts, reports, scientific translation, or feedback rounds when purpose, reader order, evidence strength, epistemic status, feedback generalization, or consistency across prose, tables, conclusions, and summaries matters. Compose with evidence and delivery skills as needed. Do not use for routine spelling, general translation, formatting-only work, or citation lookup."
metadata:
  version: "1.0.0"
---

# Scientific Writing and Revision

## Purpose

Write research prose that lets the reader identify the question, reasoning, evidence, conclusion, and limit without guessing the author's intent. Correct the scientific role and logic before polishing the sentence surface.

## Establish the Writing Contract

Identify:

- document type and audience;
- the reader's main question or decision;
- authoritative facts, verified results, hypotheses, and pending choices;
- required structure, language, citation style, and length;
- whether the task is drafting, revising, translating, responding to comments, or compressing.
- optional project extensions: an approved style guide, reporting guideline, domain terminology map, and document-type profile.

If important evidence is missing, write a scaffold or mark the gap; do not manufacture a result or citation.

## Compose with Other Skills

Document engineering and workspace-memory methods are optional companions from other groups. Select an available equivalent when a named Skill is absent; loading or completing an ordinary scientific prose task does not require installing every companion group.

Route by event rather than by a generic request to “help write”:

- call `evidence-traceable-literature-review` when a new claim must be found, a source must be verified, evidence is added or removed, or a citation delta changes support;
- use citation metadata tools for DOI and bibliography identity only;
- call the relevant domain Skill for specialist scientific or methodological judgment;
- call `research-document-delivery` when touching DOCX/PDF, review markup, cross-format synchronization, package structure, or authoritative rendering;
- call `rigorous-research-workflow` only when an upstream authority change invalidates multiple linked artifacts, exact lifecycle state must be governed, or the work needs a frozen-baseline or release transition; ordinary evidence-to-prose and prose-to-DOCX handoffs compose directly with their specialists;
- call `manage-workspace-memory` when purpose, authority, decision, blocker, or next action must persist across sessions.

Writing content remains this Skill's responsibility even when another Skill owns its evidence, file structure, or persistence.

## Resume and Extend Deliberately

For a multi-round document, inspect the current purpose contract, evidence snapshot, section/surface map, claim status, feedback decisions, and unresolved gaps before revising. Reuse valid decisions; do not replay resolved comments or restart from a blank outline unless the purpose or evidence base has been invalidated.

Project-supplied style guides, reporting guidelines, terminology maps, and document profiles are extension inputs, not content to bake into this reusable Skill. Apply the most specific authorized extension and report conflicts with the document's scientific truth or required standard.

For complex or multi-round work, use [REVISION_STATE.json.template](assets/REVISION_STATE.json.template) and its structural validator:

```text
python scripts/validate_revision_state.py revision-state.json
```

Do not create a ledger for routine wording edits. Schema 1.1 reserves the top-level `extensions` object for project-specific style, reporting, terminology, or document-profile metadata; keep common purpose, evidence, surface, claim, feedback, gap, and next-action meanings unchanged. Older records must be preserved and migrated explicitly rather than silently relabeled. The validator checks IDs, roles, and cross-surface closure and reports structural consistency only; it cannot judge whether prose is scientifically correct or well written.

## Run the Workflow

### 1. State the Main Line

Write one sentence that captures the document's central question and intended answer. Assign each section one role in that line. For longer documents, outline the argument before producing full prose.

For long or multi-round work, keep a compact purpose anchor and audit project-level requirements, the current document's responsibility, supporting material, excluded substitutes, and structural prominence after consequential edits. Read [revision-and-audit.md](references/revision-and-audit.md) for the purpose-drift and scope-boundary procedure instead of loading it for routine abstracts, captions, or translation.

Read [argument-and-language.md](references/argument-and-language.md) for paragraph logic, classifications, terminology, evidence-calibrated verbs, and multilingual style.
When revising a review, abstract, conclusion, table, or discussion summary, also apply the epistemic-status and summary-parity audit in that reference.

### 2. Separate Knowledge Roles

Mark statements as established context, unresolved gap, objective, design decision, result, interpretation, limitation, or future work. Do not present known background as the new research question, a measurement variable as the final objective, or a planned test as a finding.

### 3. Draft in Reader Order

For each paragraph, lead with its central judgment, then give evidence or design detail, explain why it matters, and close with a boundary or transition. Use this as a functional pattern, not a rigid template.

Use headings as navigation labels rather than displaced topic sentences. Keep same-level headings concise and grammatically parallel, normally as noun phrases, and leave the section's substantive judgment in an opening paragraph that remains complete when the heading is hidden.

When describing a method, connect `feature -> consequence for evidence, comparison, or validation -> role in the present argument`. An inventory of inputs, architecture, or parameters does not by itself justify a research position.

For a technical concept, prefer:

`plain-language meaning -> formal definition or source -> what it answers -> what it omits`

Before listing technical modules, establish the smallest computation chain the reader needs: `input -> intermediate object -> operation -> output`. Introduce each specialist term as `plain-language meaning -> established term -> concrete role in that chain`. If a label is author-created rather than field-standard, identify it as a local label or replace it with an established expression.

Apply a term-necessity gate before the first-use explanation. Introduce a specialist label only when the current claim, comparison, or later repeated reasoning needs it. If plain language already carries the argument or the label appears only once, omit it. If a reviewer asks what an isolated term means, decide whether to omit, relocate, or define it; do not insert a definition at the comment anchor by default. “First use” means the first functional use in the argument, not the earliest place a definition can be added.

Read [document-types.md](references/document-types.md) for document-specific structures.

### 4. Keep Taxonomies and Referents Coherent

Each list or classification must use one dimension. Separate scope, information source, mechanism, implementation tool, training target, and workflow stage rather than placing them at the same level.

Define recurring terms at first use. Replace “this,” “these,” “the above,” “another,” or “the former” when more than one antecedent is possible.

### 5. Calibrate Language to Evidence

Use causal language only when the design supports causation. Treat proxies as operational measures, not the latent state itself. State population, scale, version, and condition when they change interpretation. Different methods or inputs may create a hypothesis of complementary error; they do not establish an ensemble benefit.

Attribute synthesized judgments to their actual source. Use formulations such as “existing literature reports/indicates/suggests” when the evidence comes from published studies, especially in a conclusion that could otherwise sound like a result of the current project. Express proposed diagnostics as conditions—“if the baseline shows...” or “when the following pattern is observed”—rather than as findings already obtained.

For a review that is intended to support discussion rather than settle implementation, keep literature facts, synthesis, conditional hypotheses, approved project decisions, and open method options visibly distinct. Do not let a confident planning tone turn a candidate hierarchy, possible training component, or later comparison into an established route. Audit the conclusion and every short summary for the same evidence strength as the body.

### 6. Revise in the Right Order

Revise in this sequence:

1. scientific correctness and evidence strength;
2. document argument and section order;
3. paragraph roles and classification logic;
4. terminology, referents, and transitions;
5. sentence economy and natural phrasing;
6. formatting and typographic consistency.

Do not beautify a sentence whose purpose or evidence remains unclear.

### 7. Adjudicate Feedback and Generalize Repairs

For every comment, decide whether the diagnosis is correct, partly correct, preference-dependent, or unsupported. Preserve a valid reading problem even when the proposed fix is scientifically unsuitable.

Treat reviewer-supplied rewrites and direct tracked edits as proposed evidence of intent unless the user explicitly designates the wording as final. Preserve the intended correction, but independently choose the clearest scientifically defensible wording.

When a comment reveals a pattern, search the whole document for analogous defects and repair every justified occurrence. Read [revision-and-audit.md](references/revision-and-audit.md) for comment adjudication, compression, and whole-document checks.

Treat comments as diagnoses, not dialogue to paste into the manuscript. Use the detailed adjudication, term-placement, whole-document pattern, purpose-drift, meta-discourse, and conflicting-scope procedures in [revision-and-audit.md](references/revision-and-audit.md) when feedback affects more than a local sentence.

### 8. Translate the Argument

Before translating, identify sentence function, logical relation, variables, terminology, and evidence strength. Rebuild the sentence naturally in the target language, then back-check numbers, symbols, conditions, citations, and certainty.

### 9. Complete a Reader-Facing Audit

Confirm that:

- the main question and answer are apparent;
- the objective, contribution object, and excluded substitutes match the initial writing contract in the introduction, section tree, tables, recommendations, and conclusion;
- project-level requirements, current-document duties, supporting assets, and deferred deliverables receive proportionate and consistent emphasis;
- scope boundaries appear only where they orient the reader or hand off work, without repeated “this document does not” explanations in substantive sections or tables;
- each section and paragraph has a defensible role;
- headings are concise, parallel navigation labels and section openings remain self-contained;
- terms and classifications remain stable;
- technical lists follow an explicit input-to-output chain, every specialist label is necessary where introduced, and necessary terms are explained at their first functional use;
- method characteristics explicitly support the stated comparison or research role;
- method choices are explained when consequential;
- claims match their evidence and scale;
- abstract verbs such as “change,” “form,” “enter,” or “provide” name the affected object, the operation, and the observable result;
- reader-facing prose states the research reasoning directly rather than answering the reviewer or explaining how the document should be written;
- supporting methods are introduced by scientific function before any boundary or handoff, and literature-derived conclusions are explicitly attributed to existing evidence;
- proposed diagnostic patterns, table rows, and decision routes remain conditional until the current project has actually observed them;
- literature-derived conclusions are attributed to the reviewed evidence, while project decisions and open options are labeled separately;
- conclusions, abstracts, tables, and short summaries preserve the body text's certainty, conditions, and unresolved choices;
- numbers, units, citations, tables, figures, and translations agree;
- compression did not remove qualifiers, causal links, or transitions.

## Non-Negotiable Rules

- Accuracy outranks elegance.
- Data and verified evidence precede quantitative narrative.
- One parallel structure uses one classification dimension.
- A local complaint triggers a whole-document pattern search, but not indiscriminate rewriting.
- Preserve limiting conditions, definitions, and uncertainty when shortening.
- Replace empty significance claims with the concrete contribution or decision affected.
- Do not imitate English word order mechanically in Chinese or translate Chinese word by word into English.
- Do not optimize prose for an AI-detector score.

## Completion Standard

The document is complete when its argument is intelligible, technical terms and referents are unambiguous, claims are calibrated to the current evidence snapshot, feedback has been judged and generalized appropriately, body/tables/conclusion/abstract/summary preserve the same purpose and epistemic status, unresolved gaps are explicit, and a separate document-engineering step can verify the delivery format without reconstructing the scientific logic.
