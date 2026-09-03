# Revision and Audit

## Comment Adjudication

For each comment, record:

| Field | Question |
| --- | --- |
| Suspected issue | What exactly is difficult, ambiguous, wrong, or inconsistent? |
| Judgment | Correct, partly correct, preference-dependent, or unsupported? |
| Reason | What context, evidence, or writing rule decides? |
| Repair level | Scientific, structural, paragraph, sentence, terminology, or format? |
| Local change | What changes at the marked location? |
| Global pattern | Where else could the same defect occur? |
| Verification | How will the repair be checked? |

A reviewer may correctly identify that a passage is unclear while proposing a scientifically unsuitable rewrite. Accept the diagnosis and select the defensible repair.

Treat a reviewer-supplied sentence, example rewrite, or direct tracked edit as proposed wording unless the user explicitly declares it final. Separate the underlying intent from the literal wording, retain any authoritative factual correction, and write the best reader-facing version after adjudication. Record when a direct edit was generalized, replaced, or only partly retained.

Do not preserve the conversation with the reviewer inside reader-facing prose. Translate the diagnosis into the document's natural argument order; avoid local answer scaffolds such as a pasted question followed by “this is because.”

For a comment about an undefined, abrupt, or overtechnical term, make an explicit location decision: **omit**, **relocate**, or **define**. First identify the section question and paragraph role. Define the term at the marked sentence only when that sentence genuinely needs the concept; otherwise remove it or move it to the first passage where it supports a claim. The comment anchor identifies the reading failure, not necessarily the correct insertion point.

## Whole-Document Pattern Search

Translate a local problem into a searchable pattern. Common patterns include:

- mixed classification dimensions;
- undefined recurring terms;
- technical lists introduced before the input-to-output computation is clear;
- specialist labels introduced only so they can be defined, or definitions inserted at a review anchor before the concept has a functional role;
- field-standard and author-created labels presented without distinction;
- ambiguous “this/these/above/another” references;
- causal verbs unsupported by design;
- different metrics treated as equivalent;
- method differences described as proven complementarity;
- a known fact framed as the new research objective;
- a diagnostic presented as the endpoint;
- units, versions, populations, or denominators omitted;
- generic significance claims;
- abstract predicates that do not identify the changed object, operation, and observable consequence;
- reader-facing prose that answers the reviewer or sounds like internal writing instructions;
- sentence-like, question-like, or nonparallel headings;
- section openings that depend on a heading for sentence grammar or the central judgment;
- method feature lists that jump to a research role without explaining the consequence for comparison or validation.
- an easier proxy, workflow improvement, post-processing step, or comparison task that has silently replaced the stated research contribution.
- an explicitly required method family, training component, or validation axis that was silently demoted while another classification problem was repaired.
- a supporting method introduced primarily through “this document does not...” language rather than its positive scientific function;
- a literature synthesis phrased so that it can be mistaken for a result of the current project;
- planned diagnostic conditions written as already observed errors, especially in tables, route diagrams, recommendations, or conclusions;
- an external method described cautiously in prose but upgraded in a table to “test” or causally isolate one component.

Inspect each match in context. Search both the annotated region and the unannotated remainder, including later sections and the heading tree. Globalization means repairing justified analogues, not blindly replacing every lexical match.

## Purpose-Drift Audit

For a long document or multi-round revision, keep a one-sentence purpose anchor and four fields: objective, intended contribution, object being changed or explained, and excluded substitutes. After a structural edit or consequential comment, inspect:

- whether the introduction still states the same problem;
- whether every section advances, supports, or bounds that problem;
- whether tables and route diagrams classify candidates by the intended contribution rather than by an easier downstream workflow;
- whether recommendations name changes to the correct object;
- whether the conclusion answers the opening purpose without upgrading an auxiliary baseline, proxy, comparison, or post-processing step into the main innovation.

If drift is present, rebuild the section tree and paragraph roles before sentence polishing. Repair the full document and synchronized summaries; an opening-only disclaimer does not neutralize a conflicting body.

## Evidence-Status and Short-Summary Audit

After a global wording repair, make a small status ledger for the claims that carry the conclusion:

| Claim | Status | Source or decision authority | Allowed wording | Surfaces to check |
| --- | --- | --- | --- | --- |
| material statement | source fact / synthesis / conditional inference / project decision / open option | primary source, evidence matrix, approved protocol, or none | calibrated verb and modal form | body, table, conclusion, abstract, group summary |

This ledger is especially important when a review has been compressed or when technical paths are intentionally left for later discussion. Replace planning verbs that imply commitment with evidence-calibrated language; do not hide the unresolved choice behind a polished future-tense sentence. Literature synthesis should name the reviewed literature as its source, and an unrun diagnostic should be written as a condition.

Then compare every short-form surface with the corresponding long-form claim. The summary may be shorter, but it must preserve the same comparator, population or condition, uncertainty, and decision boundary. If a bibliography or evidence matrix changed, perform the citation-delta audit before declaring the wording repair complete.

## Scope-Boundary Meta-Discourse Audit

After correcting purpose drift, search the entire document for boundary declarations and future-work handoffs. Assign each occurrence one function: orient the opening, close a bounded supporting section, or delimit the conclusion. Normally retain no more than one of each. Delete repetitions in method comparisons, tables, validation sections, and limitations when the same boundary is already established; replace them with the direct scientific judgment, task-distance statement, selection rule, or validation condition that the paragraph actually needs.

Then measure structural prominence independently of wording. Compare heading depth, paragraph share, table rows, recommendations, and conclusion space with the current document's responsibility. A supporting method has not been successfully bounded merely because every paragraph says that it is secondary.

For each bounded supporting method, replace the first surviving disclaimer with a positive role statement: `method -> object it may affect -> evidence or comparison it contributes -> current uncertainty`. Keep a later handoff only when another deliverable must decide implementation details. In the conclusion, name “existing studies” or “the reviewed literature” before any synthesized implication that might otherwise sound like a completed experiment.

Audit diagnostic tables separately from prose. If baseline error analysis has not yet been run, make the title, first-column header, and each row conditional. Keep cross-software comparisons as hypothesis-generating references unless matched inputs and within-system module controls support causal attribution; do not let a compact table silently overstate a role that the body text correctly bounded.

## Revision Order

1. Verify claims, numbers, and evidence.
2. Repair the main argument and section order.
3. Assign one job to each paragraph.
4. Correct classifications, terms, and referents.
5. Improve transitions and sentence form.
6. Compress duplication and empty language.
7. Audit formatting and synchronized artifacts separately.

## Compression Audit

After shortening, confirm that the text still contains:

- the research gap or purpose;
- method identity and consequential choices;
- main result or planned output;
- population, condition, and scale;
- definitions and units;
- uncertainty and limitations;
- logical connectors needed to preserve argument direction.

## Final Writing Checks

- Can the main question and answer be stated in one sentence?
- Do the objective, contribution object, excluded substitutes, section tree, tables, recommendations, and conclusion still agree?
- Does every section advance the main line?
- Do same-level headings form concise, parallel navigation labels, with self-contained opening paragraphs?
- Does every paragraph make one central judgment?
- Does each method description connect its characteristics to the stated comparison, inference, or research role?
- Are parallel lists single-dimensional?
- Are recurring terms defined and stable?
- Does every technical module have a clear place in the input-to-output computation?
- Is every specialist label necessary at its point of introduction, and was each abrupt term deliberately omitted, relocated, or defined at its first functional use?
- Does every backward reference have one antecedent?
- Do consequential “change/form/enter/provide” statements name the object, operation, and observable result?
- Has reviewer dialogue and document-writing meta-discourse been removed from reader-facing prose?
- Are scope disclaimers limited to reader orientation and genuine handoffs, with supporting material receiving proportionate structural space?
- Are claims calibrated to evidence, scale, and uncertainty?
- Do the conclusion, abstract, tables, and short summaries preserve the same evidence status and unresolved decisions as the body?
- Are consequential method choices explained?
- Are numbers, units, versions, citations, and translations consistent?
- Has feedback been generalized without introducing unrelated changes?
