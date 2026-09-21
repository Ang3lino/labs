# Cross-Epic Alignment: Registry Contract Gaps

**Epic:** EPIC-05 Inference Serving — INF-05
**Raised by:** Platform Team
**Handed to:** Training Pipeline Epic owner
**Status:** Open — action required before this story can be closed in production

---

## Purpose

The INF-05 contract enforcer requires 11 fields to be present as tags on every
promoted MLflow model version. This document lists which of those fields MLflow
does **not** capture natively today, and therefore must be explicitly set by the
Training Pipeline CI/CD before promotion.

The Training Pipeline epic owns the gap items below. They must be resolved
before any production deployment can flow through the contract enforcer.

---

## Gap Analysis

| # | Contract Field | MLflow Native? | Gap / Action Required |
|---|---|---|---|
| 1 | `runtime` | No | Must be set as a custom tag in the training pipeline run. |
| 2 | `runtime_version` | No | Must be pinned and tagged at model registration time. |
| 3 | `quantization_precision` | No | Must be set when the quantized artifact is logged. |
| 4 | `tensor_parallel_degree` | No | Must be determined at evaluation time and tagged. |
| 5 | `accelerator` | No | Must reflect the GPU family used during evaluation (e.g. `L40S`). |
| 6 | `max_context` | No | Must be set to the context length the model was evaluated at. |
| 7 | `evaluated_concurrency` | No | Must reflect the concurrency target the model was load-tested at. |
| 8 | `preprocessing_tokenizer` | No | Must reference the HuggingFace tokenizer path used at inference. |
| 9 | `resource_profile` | No | Must map to a known T-shirt size (e.g. `gpu.1x`, `gpu.2x`). |
| 10 | `artifact_digest` | Partial | MLflow records a `source` URI and `run_id` but not an explicit SHA-256 of the weight files. The training pipeline must compute and tag `sha256:<hash>` of the model artifact directory at log time. |
| 11 | `owning_team` | No | Must be set at model registration. This is the attribution field the Grafana consumption dashboard depends on — it cannot be inferred after the fact. |

**Summary: 10 of 11 fields require explicit tagging by the Training Pipeline.
`artifact_digest` is partially covered but needs an explicit SHA-256 tag.**

---

## MLflow Stage Deprecation

MLflow >= 2.9 deprecates lifecycle stages (`Production`, `Staging`,
`Archived`) in favour of **aliases** (e.g. `@champion`, `@baseline`).

The current enforcer reads `current_stage` for backward compatibility.
Before MLflow stages are removed:

1. Training Pipeline must begin setting aliases alongside stages.
2. The enforcer's `VALID_PROMOTION_STATES` must be updated to recognise
   alias-based promotion (e.g. `"champion"`, `"baseline"`).
3. `mlflow_adapter._mlflow_get` must be updated to read
   `client.get_model_version_by_alias(name, alias)` instead of
   `client.get_model_version(name, version)`.

---

## Action Items for Training Pipeline Owner

- [ ] Add all 10 missing tags to the model registration step in CI/CD.
- [ ] Add SHA-256 digest computation and tagging for `artifact_digest`.
- [ ] Agree on `resource_profile` T-shirt size vocabulary with the Platform Team.
- [ ] Agree on `owning_team` naming convention (matches Grafana label).
- [ ] Plan alias migration timeline with MLflow upgrade roadmap.
