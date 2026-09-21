"""
INF-05 acceptance criteria tests.

Each test maps to an explicit AC from the story. AC numbers are noted in
comments so a reviewer can trace test → requirement directly.

These tests use enforce_contract() directly (no HTTP layer) for the
validation logic, and the FastAPI TestClient for the HTTP surface.
MLFLOW_MOCK=1 is set for all tests so no MLflow server is required.
"""

import os
import pytest

os.environ["MLFLOW_MOCK"] = "1"

from fastapi.testclient import TestClient

from src.contract_enforcer import ValidateResponse, app, enforce_contract

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _contract(promotion_state="Production", **tag_overrides):
    tags = {
        "runtime": "vllm",
        "runtime_version": "0.5.0",
        "quantization_precision": "bf16",
        "tensor_parallel_degree": "1",
        "accelerator": "L40S",
        "max_context": "8192",
        "evaluated_concurrency": "100",
        "preprocessing_tokenizer": "hf/llama3",
        "resource_profile": "gpu.1x",
        "artifact_digest": "sha256:abc123",
        "owning_team": "forecasting-squad",
    }
    tags.update(tag_overrides)
    return {"promotion_state": promotion_state, "tags": tags}


# ---------------------------------------------------------------------------
# AC: Strict Validation — missing field named explicitly
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("missing_field", [
    "runtime", "runtime_version", "quantization_precision",
    "tensor_parallel_degree", "accelerator", "max_context",
    "evaluated_concurrency", "preprocessing_tokenizer",
    "resource_profile", "artifact_digest", "owning_team",
])
def test_missing_field_rejected_with_field_name(missing_field):
    """AC: A deployment attempt against an artifact missing any field must
    fail with an error naming the specific missing field."""
    contract = _contract(**{missing_field: ""})
    result = enforce_contract(contract, "test-model", "1")
    assert result.status == "rejected"
    assert missing_field in result.reason
    assert result.manifest is None


# ---------------------------------------------------------------------------
# AC: Promotion Gating
# ---------------------------------------------------------------------------

def test_staging_artifact_rejected():
    """AC: An unpromoted artifact cannot reach the Production environment."""
    result = enforce_contract(_contract(promotion_state="Staging"), "m", "1")
    assert result.status == "rejected"
    assert "Staging" in result.reason


def test_missing_promotion_state_rejected():
    """AC: No promotion_state means the artifact is unknown — reject it."""
    result = enforce_contract(_contract(promotion_state=""), "m", "1")
    assert result.status == "rejected"
    assert "promotion_state" in result.reason


def test_production_state_accepted():
    """AC: 'Production' is a valid promotion state."""
    result = enforce_contract(_contract(promotion_state="Production"), "m", "1")
    assert result.status == "accepted"


def test_promoted_state_accepted():
    """AC: 'Promoted' is also a valid promotion state (alias-based flow)."""
    result = enforce_contract(_contract(promotion_state="Promoted"), "m", "1")
    assert result.status == "accepted"


# ---------------------------------------------------------------------------
# AC: Hardware Constraint Enforcement — TP ceiling
# ---------------------------------------------------------------------------

def test_tp_above_ceiling_rejected():
    """AC: tensor_parallel_degree above 2 must be rejected, naming the ceiling."""
    result = enforce_contract(_contract(tensor_parallel_degree="4"), "m", "1")
    assert result.status == "rejected"
    assert "2" in result.reason  # fleet ceiling named


def test_tp_at_ceiling_accepted():
    """AC: tensor_parallel_degree == 2 is allowed (the ceiling is inclusive)."""
    result = enforce_contract(_contract(tensor_parallel_degree="2"), "m", "1")
    assert result.status == "accepted"


def test_tp_zero_rejected():
    """Regression: TP=0 must be rejected — not a valid degree."""
    result = enforce_contract(_contract(tensor_parallel_degree="0"), "m", "1")
    assert result.status == "rejected"


def test_tp_non_integer_rejected():
    """TP must be parseable as an integer."""
    result = enforce_contract(_contract(tensor_parallel_degree="two"), "m", "1")
    assert result.status == "rejected"


# ---------------------------------------------------------------------------
# AC: Attribution Propagation — owning_team in manifest labels
# ---------------------------------------------------------------------------

def test_owning_team_in_manifest_labels():
    """AC: owning_team must appear in manifest metadata labels so Grafana
    can attribute GPU cost without a join."""
    result = enforce_contract(
        _contract(owning_team="data-platform"), "my-model", "3"
    )
    assert result.status == "accepted"
    labels = result.manifest["metadata"]["labels"]
    assert labels["owning_team"] == "data-platform"


def test_manifest_contains_runtime_env():
    """AC: All serving-consumed fields reach the RayService manifest."""
    result = enforce_contract(_contract(), "my-model", "1")
    assert result.status == "accepted"
    env = result.manifest["spec"]["serveConfigV2"]["applications"][0][
        "runtime_env"
    ]["env_vars"]
    assert env["RUNTIME"] == "vllm"
    assert env["ARTIFACT_DIGEST"] == "sha256:abc123"


def test_manifest_gpu_count_matches_tp():
    """AC: num_gpus in the Ray actor options must equal tensor_parallel_degree."""
    result = enforce_contract(_contract(tensor_parallel_degree="2"), "m", "1")
    assert result.status == "accepted"
    actor = result.manifest["spec"]["serveConfigV2"]["applications"][0][
        "deployments"
    ][0]["ray_actor_options"]
    assert actor["num_gpus"] == 2


# ---------------------------------------------------------------------------
# AC: HTTP surface (webhook shape)
# ---------------------------------------------------------------------------

def test_http_validate_accepted():
    """Webhook returns structured JSON for a valid model."""
    resp = client.post(
        "/validate",
        json={"model_name": "llama-3-8b-instruct", "model_version": "1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["manifest"] is not None
    assert body["manifest"]["kind"] == "RayService"


def test_http_validate_rejected_missing_field():
    """Webhook returns structured JSON for an invalid model."""
    resp = client.post(
        "/validate",
        json={"model_name": "gemma-2b", "model_version": "1"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected"
    assert body["manifest"] is None
    assert "runtime_version" in body["reason"]


def test_http_validate_unknown_model():
    """Unknown model name returns 404."""
    resp = client.post(
        "/validate",
        json={"model_name": "nonexistent-model", "model_version": "1"},
    )
    assert resp.status_code == 404


def test_http_healthz():
    """Health probe must return 200."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
