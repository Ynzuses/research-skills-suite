# Failure Recovery and Release

## Hypothesis-Based Diagnosis

Turn an anomaly into competing hypotheses and test the cheapest decisive evidence first. For example, an empty summary can reflect:

- a true zero result;
- missing or stale input;
- upstream filtering;
- identifier mismatch;
- parser failure;
- incomplete job;
- wrong path or version;
- model power limitation.

Return to raw outputs or logs before explaining the anomaly scientifically. Record disproved hypotheses so the same path is not repeated.

## Rerun Risk Assessment

Before rerunning an existing analysis, record:

1. purpose of the rerun;
2. exact scripts, inputs, and outputs affected;
3. overwrite scope and downstream consumers;
4. time and resource estimate;
5. backup or versioned output path;
6. acceptance and rollback criteria;
7. deadline impact.

Do not rerun merely because a script is available. A stable existing result may have many downstream references.

## Evidence-Bound Skips

Skipping is a reuse decision, not a successful execution. A skipped task keeps `exit_code` and `success_marker` null and records:

```json
{
  "reason": "why execution is unnecessary",
  "upstream_fingerprint": "the current input+code+environment identity",
  "verification": "how every referenced output and checkpoint was rechecked"
}
```

Place this object in `skip_record`. Its fingerprint must exactly match every referenced output's `upstream_fingerprint`, and each reused output must already be `produced` or `verified-zero`. Put prior failed attempts in `failures_and_fallbacks`; do not preserve an old exit code on the current skipped state.

## Fallback Decisions

Separate:

- technical validity;
- scientific adequacy;
- communication or publication usefulness.

A pipeline can pass a minimal scripted threshold while remaining scientifically weak. If a fallback changes the phenotype, sample, metric, endpoint, model family, or interpretation, present the tradeoff and obtain the required scientific decision instead of silently optimizing for a prettier result.

## Single-Provenance Outputs

Final academic tables and figures should be produced by one documented computation over the complete intended input. Do not combine completed rows parsed from an interrupted log with missing rows computed interactively unless the combination itself is an explicit, reproducible pipeline and all rows are equivalently verified.

## Code Change Guards

For batch or regular-expression edits:

- constrain files and exact patterns;
- count matches before and after;
- check indentation and line structure;
- run formatter or parser where appropriate;
- run syntax, AST, shell, or language validation;
- review a diff and representative behavior;
- avoid editing unrelated user changes.

## Artifact Classes

### Internal Working Code

May contain local orchestration and diagnostics but still requires privacy control and enough clarity for the team.

### Reproducibility or Archival Code

Preserves the exact analysis and environment needed to reproduce a result, including historically awkward choices when scientifically relevant.

### Collaborator or Supervisor Archive

Optimized for inspection and continuity, with stable entry points and documented data dependencies.

### Public Code

Requires portable configuration, synthetic examples, explicit license and provenance, privacy and path scanning, dependency documentation, tests, and removal of credentials or local infrastructure. Neutralize personal details without deleting useful scientific analyses or breaking code structure.

These classes can overlap but should not be selected using the same inclusion rules.
