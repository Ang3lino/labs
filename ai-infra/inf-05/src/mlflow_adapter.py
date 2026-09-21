"""
MLflow adapter for INF-05 contract enforcement.

Production path: set MLFLOW_TRACKING_URI to the real server. The real
client calls mlflow.MlflowClient().get_model_version() and returns the
version's tags and current_stage.

Mock path: set MLFLOW_MOCK=1. The mock reads test-payloads.json so the
webhook can be exercised without an MLflow server. The mock lookup is by
model_name — the version string is accepted but not filtered on, matching
how MLflow would return the latest promoted version.

MLflow stage deprecation note (see cross_epic_gaps.md):
  MLflow >=2.9 deprecates stages (Production/Staging/Archived) in favour
  of aliases (@champion, @baseline). The current_stage field is surfaced
  here for backward compat. Teams migrating to aliases must update
  VALID_PROMOTION_STATES in the enforcer and map alias names here.
"""

import json
import os
from pathlib import Path


def get_model_contract(model_name: str, model_version: str) -> dict:
    """
    Return {"promotion_state": str, "tags": dict[str, str]} for the given
    model version. Raises on MLflow connectivity failure or unknown model.
    """
    if os.getenv("MLFLOW_MOCK", "0") == "1":
        return _mock_get(model_name)
    return _mlflow_get(model_name, model_version)


# ---------------------------------------------------------------------------
# Real MLflow path
# ---------------------------------------------------------------------------

def _mlflow_get(model_name: str, model_version: str) -> dict:
    import mlflow  # only imported when not mocked — keeps tests fast

    client = mlflow.MlflowClient()
    mv = client.get_model_version(model_name, model_version)
    return {
        "promotion_state": mv.current_stage,  # "Production" | "Staging" | …
        "tags": dict(mv.tags),
    }


# ---------------------------------------------------------------------------
# Mock path (test / PoC)
# ---------------------------------------------------------------------------

def _mock_get(model_name: str) -> dict:
    payloads_path = Path(__file__).parent.parent / "test-payloads.json"
    payloads = json.loads(payloads_path.read_text())
    for payload in payloads.values():
        if payload.get("model_name") == model_name:
            return {
                "promotion_state": payload.get("promotion_state", ""),
                "tags": payload.get("tags", {}),
            }
    raise KeyError(f"Model '{model_name}' not found in test-payloads.json")
