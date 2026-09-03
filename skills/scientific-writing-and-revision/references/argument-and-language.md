# Argument and Language

## Contents

- [Build the Main Line](#build-the-main-line)
- [Paragraph Architecture](#paragraph-architecture)
- [Heading Architecture](#heading-architecture)
- [Method-to-Judgment Bridge](#method-to-judgment-bridge)
- [Mechanism-First Technical Explanation](#mechanism-first-technical-explanation)
- [Classification Discipline](#classification-discipline)
- [Terminology and Reference](#terminology-and-reference)
- [Evidence-Calibrated Language](#evidence-calibrated-language)
- [Epistemic Status and Summary Parity](#epistemic-status-and-summary-parity)
- [Concrete Change Statements](#concrete-change-statements)
- [Informative Scientific Style](#informative-scientific-style)
- [Chinese and English](#chinese-and-english)

## Build the Main Line

Use the smallest complete chain appropriate to the document:

`established context -> unresolved gap -> objective -> evidence or design -> verified result or planned output -> inference boundary`

Known background should motivate the new question rather than masquerade as the research objective. A variable or proxy is part of the design; the objective states the relation, estimate, contrast, or decision the study seeks to produce.

## Paragraph Architecture

One paragraph should make one central scientific judgment. A useful internal sequence is:

1. main judgment;
2. evidence, result, or concrete design statement;
3. explanation of relevance;
4. boundary, implication, or transition.

Split a paragraph when it changes scientific role, evidence base, or classification dimension. Merge fragments that do not carry a complete judgment on their own.

Connections such as “therefore,” “however,” “in this context,” and “by contrast” are useful only when they expose a real causal, contrastive, sequential, or scope relation. Do not add them by quota, but do not delete necessary logic during compression.

## Heading Architecture

Use headings to expose the document map, not to carry sentence grammar or substitute for a topic sentence. Prefer concise noun phrases, and keep headings at the same level parallel in syntax and scope. Avoid questions, complete claims, and fragments clipped from the first sentence merely to make them look shorter.

Audit headings twice: read the heading tree alone for hierarchy and parallelism, then hide each heading mentally and confirm that the opening paragraph remains grammatically complete and states the section's substantive judgment. If the paragraph depends on the heading to supply its subject, predicate, contrast, or conclusion, return that material to the prose.

## Method-to-Judgment Bridge

After describing a method's input, information source, model, training procedure, or output, state what those characteristics change. A useful chain is:

`method characteristic -> consequence for observable evidence, comparability, or generalization -> role in the present study or synthesis`

For example, participation of evaluation cases in model fitting affects whether a workflow is comparable to a frozen inductive model. The label assigned to the workflow should follow from that consequence, not appear abruptly after a feature list.

## Mechanism-First Technical Explanation

Before presenting a catalogue of modules, reconstruct the minimum computation visible to the reader:

`observed input -> candidate or intermediate representation -> update or transition -> probability, estimate, or decision output`

Locate each module on this chain and state what object it reads, what operation it performs, and which output can change. A bare list of emissions, states, transitions, gates, residuals, or ablations is not a mechanism explanation, even when every term is standard within the field.

At first use, explain a specialist term in this order:

`plain-language meaning -> field-standard term or abbreviation -> concrete role in the present computation`

If a phrase is a local analytic label rather than an established technical term, mark it as a local label and define its boundary, or replace it with a concrete description. Do not make readers guess whether a phrase is standard nomenclature or author shorthand.

Run a necessity and placement test before defining any label. Ask whether the surrounding claim needs the term, whether later reasoning reuses it, and whether this is the first place the concept performs a real argumentative function. Omit a one-off label when plain language is sufficient; relocate a necessary definition to its first functional use. A reviewer question about an abrupt term can be resolved by deleting or moving the term, not only by adding an explanation beside it.

## Classification Discipline

Before presenting a taxonomy, name the dimension. Examples include:

- application scope;
- input or information source;
- model mechanism;
- implementation tool;
- workflow stage;
- training target;
- evidence type;
- intended use.

Test whether every item can complete the same sentence after the same upper-level definition. If one item answers “where does it act,” another “what tool implements it,” and another “what does it predict,” the hierarchy is mixed and must be separated or displayed as a matrix.

Differences in algorithms, evidence, or information sources justify testing whether errors differ. They do not by themselves establish complementarity, routing benefit, or ensemble gain.

## Terminology and Reference

Define high-frequency technical terms at first use with an operational boundary. A glossary supports later checking but cannot repair an undefined term in the opening argument.

Use one preferred term per concept. If two terms are not synonyms, state the distinction. A pronoun or backward reference must have exactly one plausible antecedent at the same logical level; otherwise repeat the technical noun.

## Evidence-Calibrated Language

Match verbs to evidence:

- measured or directly observed: “observed,” “measured,” “estimated”;
- replicated compatible evidence: “supports” or “consistently showed under…”;
- plausible interpretation: “is consistent with,” “suggests,” or “may reflect”;
- plan or hypothesis: “will evaluate,” “may,” or “remains to be tested”;
- bounded non-finding: “was not established” or “was not identified in this search.”

Do not convert association into cause, a proxy into a biological state, a coarse group average into a local effect, or a future analysis into a completed result.

## Epistemic Status and Summary Parity

Before a document-wide revision, label each consequential statement with one status:

| Status | What it can say | What it must not imply |
| --- | --- | --- |
| source-reported fact | the cited study reported, measured, or defined | that the current project reproduced it |
| review synthesis | the reviewed evidence converges, differs, or leaves a gap | that the synthesis is a new experiment |
| conditional inference | if a specified pattern is observed, it would support or motivate a comparison | that the pattern has already been observed |
| project decision | the user or approved protocol has fixed a choice | that a literature review established the choice |
| open option or handoff | a candidate can be evaluated or discussed in a later deliverable | that implementation, training, or route selection is settled |

Choose verbs, tense, and nouns from the status rather than from the desired future direction. In a review prepared for group discussion, use terms such as “候选”“可能”“可供比较”“有待检验” and “取决于后续评估” when the evidence only supports a bounded option. Reserve “采用”“确定”“验证了” and equivalent declarative wording for an explicit project decision or an actually completed analysis.

Run a summary-parity check after revising an abstract, conclusion, table, slide, or group message. Each short-form statement must retain the source attribution, conditions, uncertainty, and decision boundary of the longer text. A concise summary may omit detail, but it may not upgrade a literature-derived suggestion into a fixed technical route or an unrun diagnostic into a result.

## Concrete Change Statements

Audit abstract predicates such as “change,” “form,” “enter,” “provide,” “affect,” and “optimize.” Each consequential sentence should answer:

1. Which object changes?
2. Through which operation or comparison?
3. Which observable quantity, decision, or boundary differs?

Replace “the method changes the output” with the relevant outcome, such as retained sites, selected hard calls, posterior probabilities, calibration, runtime, or error distribution. Replace “information enters the model” with the actual representation and computation that consumes it. Abstract verbs are acceptable only when the object and consequence are already unique and explicit.

## Informative Scientific Style

Replace “has important significance,” “provides an important reference,” and “lays a foundation” with the specific output, uncertainty, decision, or method improvement affected.

Explain method choices when alternatives would change interpretation. Lead with what the research does; use prohibitions only when explaining a genuine methodological risk and pair them with cause, consequence, and the adopted design.

For non-model organisms or less-studied domains, describe intrinsic biological or data complexity rather than using “backward,” “lagging,” or other deficit narratives. Define gaps at the intersection of population, organism, trait, method, scale, and validation condition instead of claiming a field is empty.

## Chinese and English

For Chinese prose:

- use explicit subjects and natural Chinese information order;
- retain field-standard abbreviations where they improve readability;
- avoid stacked nominal modifiers and unnecessary translated syntax;
- use the domain's established measure words and terminology;
- keep causal and contrastive links visible.

For English prose:

- keep subject, action, and object close;
- use parallel grammar for parallel scientific roles;
- avoid inflated novelty or certainty;
- check tense, countability, articles, symbols, and unit formatting after logic is stable.

Translation preserves argument, scope, and certainty before surface wording. Back-check every number, range, sample size, version, and citation.
