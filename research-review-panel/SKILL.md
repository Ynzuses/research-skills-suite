---
name: research-review-panel
description: "Challenge a research artifact with several independent reviewers before it is submitted, frozen, or acted on. Use when a manuscript, literature review, analysis plan, statistical or method decision, scientific code, or figure needs a pre-submission stress test, a second opinion from another model, competing explanations of an unexpected result, or reconciliation of conflicting reviews. Reviewers work separately and cite locations; findings are settled against primary evidence, not by votes. Do not use for proofreading, a quick single-pass check, applying feedback already received, or software-only code review with no research claim."
metadata:
  version: "1.1.0"
---

# Research Review Panel

## Purpose

A single reader, or a model reading its own work, tends to confirm what is already on the page. Adding reviewers does not fix this by itself: reviewers that talk before they read converge on the first opinion, and copies of one model share the same blind spots. This Skill sets up the conditions under which several reviewers add information. They read separately, they differ from one another, they point to locations, and each disputed finding is settled by opening the evidence.

The output is an adjudicated list of findings and decisions. The artifact changes afterwards, in one hand.

## Decide Whether a Panel Is Warranted

A panel costs several times a single review. Use it where an error is expensive to discover later:

- before formal circulation: a submission, a report to a supervisor or client, a frozen baseline, a public release;
- before a decision that is costly to reverse: a statistical model, an evaluation protocol, a data split, a reference dataset;
- when a result is unexpected and its first explanation arrived quickly;
- when earlier reviews disagree with each other.

Use one independent reviewer for moderate stakes and no panel for routine edits. State which was chosen and why.

## Core Rules

1. **Independence before exchange.** Every reviewer finishes a written review before seeing another review, the author's defense, or any summary of opinions.
2. **Reviewers must differ.** Prefer, in this order, a different model family, then a different lens with different materials, then a different role under the same model. Two runs of one model with one brief count as one reviewer.
3. **Findings are located.** Each finding names a place in the artifact and, where it concerns support, a place in the source, data, or code. A finding without a location is a question, not a finding.
4. **Evidence decides.** A dispute is settled by opening the cited passage, table, script, or output. The number of reviewers who agree, a reviewer's confidence, and the reputation of a model are not evidence.
5. **A position changes only for a stated reason.** During cross-examination a reviewer withdraws or revises a finding only by citing something it had not considered. A change with no stated reason is recorded as conformity and discounted.
6. **Reviewers read; one author writes.** Reviewers do not edit the artifact. Accepted findings go to a single writer so that repairs stay consistent.
7. **Rounds are bounded.** One cross-examination round is the default and two is the limit. What remains disputed goes to adjudication or to the person who owns the decision.

## Workflow

### 1. Frame the Review

Record the artifact's identity (path, version, and hash when it is frozen), its purpose and reader, the claims or decisions at stake, the authorities reviewers may consult (sources, data, scripts, the design record), what is out of scope, and which material may leave the machine. Reviewers that are not told the purpose review against their own.

### 2. Compose the Panel

Three or four reviewers suit most artifacts. Choose lenses that fail in different ways, and include one reviewer whose only task is to build the strongest case that the artifact should not go forward. Read [panel-design.md](references/panel-design.md) for lenses by artifact type, panel size, and the diversity ladder. Give every reviewer the same frame and its own lens with [reviewer-brief.md](assets/reviewer-brief.md).

### 3. Run the Independent Pass

Start the reviewers in separate contexts, in parallel where the host allows. Each returns located findings with a severity, the evidence it opened, and what it could not check. Do not relay partial results between reviewers.

### 4. Consolidate Without Deciding

Merge duplicate findings and keep a record of who raised each. Keep findings raised by a single reviewer. Note whether reviewers who agree examined the same passage; agreement that rests on one passage is one observation. No finding is dropped at this step.

### 5. Cross-Examine Once

Give each reviewer the consolidated findings without the names or the number of reviewers behind each one. For every material finding it did not raise, the reviewer tries to refute or confirm it against the artifact; it also re-examines its own. Skip this step when the independent findings do not conflict and all of them can be checked directly.

### 6. Adjudicate Against Evidence

For every finding that would change the artifact, the adjudicator opens the cited location and records a verdict (confirmed, confirmed in part, refuted, or unverifiable) and then a decision (accept, accept in modified form, reject with a reason, or refer to the owner). A minority finding that the evidence confirms is accepted. A majority finding that the evidence refutes is rejected. An unverifiable finding stays open; it is not a pass. Read [adjudication.md](references/adjudication.md) and keep the record in [review-ledger.tsv](assets/review-ledger.tsv).

Decisions that belong to a person, such as a change of research question, a method choice with scientific trade-offs, or anything a supervisor must approve, are referred with the evidence attached.

### 7. Repair and Recheck

Hand accepted findings to the method that owns the artifact: the writing method for prose, the evidence method for claims and citations, the computational method for code and results, the delivery method for files. When a finding recurs, repair every instance, not only the located one. A repair changes the artifact, so the earlier review no longer covers the changed parts; review those parts again, with a reviewer that has not seen the repair rationale when the stakes warrant it.

### 8. Close

Report the panel's composition and how its reviewers differed, the number of findings by verdict, the accepted changes, the rejected findings with reasons, the open items and their owners, the checks that were not run, and the limits of the review.

## Reviewers from Another Model Family

A reviewer from another family is the strongest source of independence a host can offer. Reach it through whatever the host provides: a plugin, a command-line tool, or an API.

- Apply the workspace's privacy rule before anything is sent. Unpublished data, individual-level records, and unpublished ideas may not be eligible. Send the minimum the lens needs, and record what was sent and to which service.
- The external reviewer has not read the workspace's rules and does not apply changes. Its output enters consolidation like any other review.
- Adjudicate its findings one by one. Adopting another model's review wholesale can lower quality as easily as raise it.
- When no other family is available, vary the lens and the materials instead, and state in the closing report that the panel shared one model.

## Competing Explanations for an Unexpected Result

When the task is to explain a surprising result, assign each reviewer one candidate explanation. Always include a pipeline or data error and the possibility that the result is real. Each reviewer states the observation that would refute its explanation and proposes the cheapest check that separates it from the others. Cross-examination targets the other explanations. Adjudication consists of running those checks or inspecting existing outputs. Report the surviving explanation as not yet refuted, not as proven.

## Practices to Refuse

- showing reviewers a draft consensus or the author's defense before they read;
- settling a dispute by counting reviewers;
- a judge that rules from summaries without opening the evidence;
- further rounds until everyone agrees;
- accepting every finding in order to appear responsive;
- reviewers editing the artifact directly;
- describing a panel of identical reviewers as independent;
- sending restricted material to an external service to obtain a second opinion.

## Compose with Other Skills

This Skill organizes the challenge and the adjudication. It does not replace the methods that produce or repair the artifact. Named companions are optional and separately installed; use the host's equivalent when one is missing.

- `scientific-writing-and-revision` for repairs to argument and prose, and for handling feedback from human reviewers;
- `evidence-traceable-literature-review` for search, screening, and claim-to-source verification;
- `reproducible-computational-research` for code, provenance, and result audits;
- `research-document-delivery` for the files that carry the repaired content;
- a workspace-memory method for recording the frozen identity that was reviewed and the next action.

## Completion Gate

Do not report a panel review as complete until:

- the frame names the artifact identity, purpose, claims at stake, and what could leave the machine;
- every reviewer wrote its review before seeing any other;
- the closing report states how the reviewers differed, including when they shared one model;
- every finding that changed the artifact has a location, a verdict reached by opening the evidence, and a decision with a reason;
- no dispute was settled by counting, and position changes without a stated reason were discounted;
- unverifiable findings and referred decisions are listed as open, with an owner;
- repaired parts were reviewed again or are listed as not re-reviewed;
- anything sent to an external service was eligible under the workspace's rule and is recorded.
