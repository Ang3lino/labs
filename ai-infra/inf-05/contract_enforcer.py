"""
INF-05: Registry Contract Enforcement Webhook

Exposes POST /validate — the deployment gate between MLflow and KubeRay.
A promotion in MLflow triggers a call to this endpoint. The webhook reads
the artifact's 11 contract fields, applies all enforcement rules, and
returns either a RayService manifest (accepted) or a structured rejection
with the exact failing field named.

Usage:
  uvicorn contract_enforcer:app --host 0.0.0.0 --port 8080

Environment:
  MLFLOW_TRACKING_URI  MLflow server URL (default: http://localhost:5000)
  MLFLOW_MOCK=1        Use test-payloads.json instead of real MLflow
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from manifest_builder import build_rayservice_manifest
from mlflow_adapter import get_model_contract

app = FastAPI(
    title="INF-05 Contract Enforcer",
    description="Deployment gate between MLflow and KubeRay.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "runtime",
    "runtime_version",
    "quantization_precision",
    "tensor_parallel_degree",
    "accelerator",
    "max_context",
    "evaluated_concurrency",
    "preprocessing_tokenizer",
    "resource_profile",
    "artifact_digest",
    "owning_team",
]

VALID_PROMOTION_STATES = {"Production", "Promoted"}
MAX_TP_DEGREE = 2


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ValidateRequest(BaseModel):
    model_name: str
    model_version: str


class ValidateResponse(BaseModel):
    status: str           # "accepted" | "rejected"
    reason: str
    manifest: Optional[dict] = None


# ---------------------------------------------------------------------------
# Validation logic (pure, no I/O — imported by tests directly)
# ---------------------------------------------------------------------------

def enforce_contract(contract: dict, model_name: str, model_version: str) -> ValidateResponse:
    """
    Apply all enforcement rules to a contract dict.
    Returns a ValidateResponse; never raises.
    """
    promotion_state = contract.get("promotion_state", "")
    if not promotion_state:
        return ValidateResponse(
            status="rejected",
            reason=f"'{model_name}' v{model_version} has no promotion_state. "
                   "Cannot deploy an artifact without a known promotion state.",
        )
    if promotion_state not in VALID_PROMOTION_STATES:
        return ValidateResponse(
            status="rejected",
            reason=f"Promotion state '{promotion_state}' is not valid. "
                   f"Must be one of {sorted(VALID_PROMOTION_STATES)}.",
        )

    tags = contract.get("tags", {})

    for field in REQUIRED_FIELDS:
        if not tags.get(field):
            return ValidateResponse(
                status="rejected",
                reason=f"Missing required contract field: '{field}'.",
            )

    try:
        tp = int(tags["tensor_parallel_degree"])
    except (ValueError, KeyError):
        return ValidateResponse(
            status="rejected",
            reason="'tensor_parallel_degree' must be an integer.",
        )

    if tp < 1:
        return ValidateResponse(
            status="rejected",
            reason=f"'tensor_parallel_degree' must be >= 1, got {tp}.",
        )
    if tp > MAX_TP_DEGREE:
        return ValidateResponse(
            status="rejected",
            reason=f"Tensor-parallel degree {tp} exceeds fleet ceiling of "
                   f"{MAX_TP_DEGREE} (L40S PCIe — no NVLink).",
        )

    manifest = build_rayservice_manifest(model_name, model_version, tags)
    return ValidateResponse(
        status="accepted",
        reason="Contract validation passed.",
        manifest=manifest,
    )


# ---------------------------------------------------------------------------
# HTTP endpoint
# ---------------------------------------------------------------------------

@app.post("/validate", response_model=ValidateResponse)
def validate(req: ValidateRequest) -> ValidateResponse:
    try:
        contract = get_model_contract(req.model_name, req.model_version)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"MLflow unreachable: {e}")

    return enforce_contract(contract, req.model_name, req.model_version)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
