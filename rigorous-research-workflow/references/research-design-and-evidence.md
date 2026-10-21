# Research Design and Evidence Interface

Use this reference when a design or evidence authority enters, leaves, or changes a governed research lifecycle. Domain specialists own scientific design, search, statistics, genomics, and benchmark methodology; this reference owns only the cross-stage contract and invalidation boundary.

## Required Input Contract

Before advancing from `scoped` toward `evidence-ready`, identify:

| Field | Required meaning |
| --- | --- |
| Purpose-contract ID | Stable question, intended contribution, audience, and disallowed substitutes |
| Design authority | Approved design/version and the specialist or decision owner |
| Evidence or analysis authority | Versioned source ledger, dataset/run identity, or explicit pending state |
| Unit and scale | The level at which downstream claims are allowed |
| Development/evaluation boundary | Groups, data, or evidence withheld from design decisions |
| Planned outputs | Claims, estimates, tables, figures, or decisions downstream consumers may expect |
| Open gaps | Missing facts or choices that prevent a later gate |

Do not manufacture domain decisions to fill a handoff. Route unresolved methodology to the relevant specialist and keep the lifecycle at its current state.

## Evidence-Ready Gate

The gate may pass only when:

- the design and evidence identities are explicit and mutually compatible;
- the specialist checks required by the task have passed;
- important claims have traceable authorities and declared epistemic status;
- units, scales, denominators, versions, and evaluation boundaries are available to downstream writers or analysts;
- contradictory evidence and material gaps remain visible;
- every downstream surface that is still valid, stale, missing, or blocked is named.

A literature search result, data file, or analysis output is not automatically `evidence-ready`; the relevant specialist must establish its fitness for the intended claim.

## Change and Invalidation Interface

When an upstream item changes, record the old and new identity, reason, decision owner, affected surfaces, and revalidation owner.

| Changed authority | Minimum downstream review |
| --- | --- |
| question, scope, estimand, unit, or design | evidence/analysis plan, claims, outline, tables, figures, summaries, and delivery |
| source added, removed, contradicted, or reassigned | evidence ledger, citation mapping, prose, conclusions, short summaries, and source package |
| data, code, metric, denominator, or result | result claims, uncertainty, tables, figures, interpretation, and derived deliverables |
| evaluation or privacy boundary | development decisions, held-out validity, public examples, logs, and release eligibility |

Invalidate first, then repair. A downstream artifact may remain current only when its owner can show that the upstream change does not affect its content or gate.

## Handoff Output

Provide the next specialist with the current purpose, authoritative identities, allowed claim scale, unresolved gaps, invalidated surfaces, required checks, and one executable next action. Do not copy specialist manuals or entire evidence packages into the orchestration record; link their authoritative artifacts instead.
