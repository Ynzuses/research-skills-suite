# Workflow State and Invalidation Contract

## Schema 2.0

`WORKFLOW_STATE.json` schema 2.0 closes the link between an upstream change, the downstream artifact it invalidates, the checks required to make that artifact current again, and the lifecycle transition that records the event. The validator rejects any other schema version. Preserve an older record as historical evidence and migrate it explicitly; do not relabel a 1.0 file without reconstructing its invalidations from the underlying decisions and artifacts.

Keep project- or domain-specific additions under the top-level `extensions` object. Common lifecycle, authority, invalidation, transition, privacy, and gate meanings must not be redefined by an extension.

## Invalidation Record

Each item in `invalidations` has this portable shape:

```json
{
  "invalidation_id": "invalidation:report",
  "target_id": "report:one",
  "trigger_event_id": "decision:corrected-analysis",
  "trigger_evidence": "decisions/corrected-analysis.md",
  "reason": "The denominator changed and the report is stale.",
  "previous_identity": {
    "identity": "report:v1",
    "sha256": null
  },
  "critical": true,
  "status": "open",
  "required_rechecks": ["analysis", "claims", "tables", "rendered-delivery"],
  "resolution": null,
  "waiver": null,
  "extensions": {}
}
```

`target_id` must resolve to a current authority ID or a stable ID in `purpose_contract.required_outputs`. Use a logical identity when the target is not one exact file; add the exact SHA-256 when the invalidated baseline is a materialized file. `trigger_evidence` is a portable relative locator to the decision or primary record that caused invalidation. `required_rechecks` names the specialist gates that must be repeated, not generic assurances such as “reviewed.”

Every invalidation must appear in at least one transition's `invalidated` list. Removing the record is not resolution.

## Resolution and Waiver

An open invalidation has null `resolution` and `waiver`, and the workflow remains in `revision-round`. A resolved invalidation records:

```json
{
  "replacement_target_id": "report:one",
  "new_identity": "report:v2",
  "completed_rechecks": ["analysis", "claims", "tables", "rendered-delivery"],
  "evidence": ["audit/report-v2-release.json"],
  "resolved_by": "research lead",
  "resolved_at": "2026-08-20T14:00:00+08:00"
}
```

Every required recheck must appear in `completed_rechecks`, and the replacement target must resolve to the current authority/output set. The evidence locators should lead to the specialist records that prove the checks for the new identity.

Only a noncritical invalidation may be waived. A waiver records a concrete reason, authorized role, time-zone-aware decision time, residual risk, and a relative evidence locator. A waiver does not convert a failed required check into a pass. If the invalidation affects scientific correctness, privacy, a frozen identity, or a required delivery/release gate, mark it critical and resolve it.

## State Gate

- `revision-round` requires at least one open invalidation.
- Any other lifecycle state rejects open invalidations.
- Resolved and permitted waived records remain in the ledger for traceability.
- A transition may cite only declared invalidation IDs, and every declared invalidation must be cited by a transition.

The structural validator cannot prove that a new analysis is correct, that prose implements the repaired evidence, or that a render is acceptable. Each referenced specialist completion gate remains authoritative for that judgment.
