# Adjudication

Adjudication turns reviewers' findings into decisions. Its one fixed requirement is that the adjudicator opens the evidence. A ruling made from the reviews alone is another opinion.

## Who Adjudicates

The lead agent adjudicates findings that can be checked against the artifact and its authorities. A person adjudicates what is theirs to decide: the research question, a method choice with scientific trade-offs, anything a supervisor, client, or co-author must approve, and any finding the lead agent cannot check. Refer these with the finding, the evidence, and the options; do not pre-empt them.

The adjudicator should not be the reviewer that raised the finding. When the lead agent also wrote the artifact, say so in the closing report: an author adjudicating its own work is the weakest arrangement, and blocking findings it rejects should be referred.

## The Ledger

Keep one row per consolidated finding in `review-ledger.tsv`.

| Field | Content |
| --- | --- |
| `finding_id` | Stable identifier for this review round |
| `artifact_location` | Section, paragraph, line, table, figure, or file and line |
| `statement` | What is wrong or unsupported, in one or two sentences |
| `lens` | The lens under which it was raised |
| `raised_by` | Reviewer identifiers; kept from other reviewers during cross-examination |
| `severity_proposed` | Blocking, major, minor, or question |
| `evidence_location` | Where the adjudicator looked: source and page, data file and row, script and line, output file |
| `cross_examination` | Upheld, contested, withdrawn with reason, withdrawn without reason, or not run |
| `verdict` | Confirmed, confirmed in part, refuted, or unverifiable |
| `decision` | Accept, accept modified, reject, or refer |
| `decision_reason` | What the evidence showed; for a referral, to whom and why |
| `repair_reference` | Where the repair was made, or the open item that tracks it |
| `status` | Open, repaired, re-reviewed, or closed without change |

## Verdict Rules

- **Confirmed.** The evidence shows what the finding says.
- **Confirmed in part.** The defect exists but is narrower, or less severe, than stated. Record the part that stands.
- **Refuted.** The evidence shows the artifact is right. Record what was opened, so the same finding is not raised again.
- **Unverifiable.** The evidence could not be opened or does not settle the point. The finding stays open and is listed in the closing report. It does not count for or against the artifact.

Apply these without regard to how many reviewers raised the finding:

- A finding from one reviewer that the evidence confirms is accepted.
- A finding from every reviewer that the evidence refutes is rejected.
- When reviewers agree because they examined the same passage, that is one observation; check it once and do not treat the agreement as added weight.
- A reviewer's stated confidence does not change a verdict.

## Reading Cross-Examination

Cross-examination produces evidence only when a reviewer cites something. Classify each change of position:

| What happened | How to use it |
| --- | --- |
| A reviewer refutes another's finding by citing a location | Open that location; this is new evidence. |
| A reviewer withdraws its own finding and cites what it had missed | Treat the finding as contested and check the cited location. |
| A reviewer withdraws or softens its finding with no citation | Record as conformity. Adjudicate the original finding as if it had not been withdrawn. |
| A reviewer adopts another's finding with no check of its own | No added weight. |
| Reviewers still disagree after the round | Adjudicate directly. Do not run rounds until they agree. |

When more than half of the position changes in a round carry no citation, note in the closing report that the round showed conformity and rest the outcome on the independent pass and the adjudicator's own checks.

## Findings from an External Model

Treat them as proposals from a reviewer that has not read the workspace's rules and cannot see what was withheld from it. Check each against the evidence before accepting it. Reject a finding that depends on material the reviewer was not given, and note that it could not have known. Do not let an external reviewer's fluent, confident report stand in for the check.

## Rejecting Findings

Rejection needs a reason that a later reader can check: the location opened and what it shows. “Out of scope” is a valid reason only when the frame excluded the point before the review began. Do not accept a finding merely to avoid explaining a rejection, and do not reject one because the repair is inconvenient.

## After Repair

A repair changes the artifact. For each accepted finding, record where the repair was made and mark the earlier review as not covering that part. Re-review the changed parts when the finding was blocking or major. The re-reviewer receives the repaired artifact and the original finding, not the author's account of the repair.

When the same defect was found in several places, search for the remaining instances before closing; a panel samples, it does not enumerate.

## Closing Report

- artifact identity reviewed;
- reviewers, their lenses and materials, and which rung of the diversity ladder was reached;
- findings by verdict and by severity;
- accepted changes and where they were made;
- rejected findings with reasons;
- open items: unverifiable findings and referred decisions, each with an owner;
- checks that were not run;
- whether cross-examination showed conformity;
- what was sent to any external service.

The report states what the panel examined. It does not certify the artifact: a panel that found nothing in the parts it read says nothing about the parts it did not.
