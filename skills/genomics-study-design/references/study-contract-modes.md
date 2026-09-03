# Study Contract Modes

## Select the Mode Before the Tools

`study_mode` states which part of the genomics workflow the study owns. It prevents a downstream-only or reference-only study from inventing upstream tools merely to satisfy a template.

| Mode | Mapping and calling | Development–held-out split |
| --- | --- | --- |
| `variant-discovery` | Always `applicable`; aligner, caller, ploidy, callable space, interval strategy, and stepwise counts are required | Required when any data-dependent selection or tuning occurs; otherwise justify `not-applicable` or declare an independently motivated split |
| `existing-genotypes` | May be `not-applicable` when the contract begins from a fixed call set | Determined by selection, tuning, and the estimand rather than by mode alone |
| `association-only` | May be `not-applicable` when upstream calls are fixed inputs | May be `not-applicable` only when models, covariates, thresholds, and other choices are prespecified and the estimand does not require held-out performance |
| `reference-audit` | May be `not-applicable` when no reads are mapped and no variants are called | Usually may be `not-applicable`, but a learned or tuned audit classifier still requires isolation |

Mode labels do not waive scientific requirements. If an `existing-genotypes` study remaps reads or recalls variants, its mapping module is applicable. If a `reference-audit` tunes thresholds against known outcomes, its split is applicable.

## Declare Selection and Tuning Directly

Use `selection_and_tuning.required` to report whether any decision is learned from the study data. Activities include reference construction, threshold selection, feature selection, covariate choice, parameter tuning, model selection, or another data-dependent decision. List the actual activity IDs rather than choosing a generic sentinel.

When `required` is `true`:

- `activities` is non-empty;
- `split.applicability` is `applicable`;
- development and held-out groups are disjoint and non-empty;
- every activity appears in `split.protected_from`;
- `verification` points to a leakage audit.

When `required` is `false`, keep `activities` empty and explain what was prespecified in `rationale`. The split may still be applicable for external validation, prospective performance, or another estimand-level reason.

## Encode Inapplicability Without Fake Values

An inapplicable conditional module uses:

```json
{
  "applicability": "not-applicable",
  "reason": "The study consumes a versioned genotype call set and performs no read mapping or variant calling."
}
```

The reason must describe the design fact that makes the module irrelevant. `none`, `N/A`, `not needed`, an unresolved placeholder, or a restatement such as `no mapping` is not a reason. Tool, path, group, and verification fields must be omitted, null, or empty as appropriate. Do not populate them with `none`, `not-applicable`, invented software, dummy groups, or fake paths.

An applicable module sets `reason` to null and fills its operational fields. `variant-discovery` cannot mark mapping and calling not applicable.

## Close Hypotheses Through Validated Outputs

Use stable IDs to form this chain:

```text
hypotheses.required_evidence_ids
  -> evidence_requirements.evidence_id
  -> evidence_requirements.output_ids
  -> expected_outputs.output_id
  -> evidence_requirements.validation_ids
  -> validations.validation_id and validations.output_ids
```

Each declared evidence requirement is used by a hypothesis. Each structured output is required by evidence and covered by an evidence-linked validation. Each validation names the output it checks and has an observable acceptance criterion. Duplicate, dangling, orphaned, or cross-linked validation IDs fail structural validation.

This closure proves that the design has specified what will adjudicate each hypothesis and how that product will be checked. It does not prove the evidence is biologically adequate; review the scientific rationale separately.

## Extend Without Breaking the Common Contract

Keep species-, platform-, consortium-, or assay-specific fields under the nearest `extensions` object. Do not replace common IDs, applicability states, version fields, leakage controls, or acceptance criteria with an extension. Top-level `extensions` is for study-wide additions; conditional-module extensions remain inert when that module is not applicable unless they only document the inapplicability decision.
