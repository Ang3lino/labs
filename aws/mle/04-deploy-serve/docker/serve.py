from __future__ import annotations

import os
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


# ponytail: FastAPI instead of Flask — lighter, async-native
DEFAULT_MODEL_PATH = "/opt/ml/model/model.pt"
FEATURE_NAMES: tuple[str, ...] = tuple([f"V{i}" for i in range(1, 31)] + ["Amount"])


class InvocationRequest(BaseModel):
    features: dict[str, float] = Field(description="Feature map containing V1..V30 and Amount")


app = FastAPI(title="Fraud Model Serve")
_model: torch.nn.Module | None = None


def _load_model() -> torch.nn.Module:
    model_path = os.getenv("MODEL_PATH", DEFAULT_MODEL_PATH)
    loaded = torch.jit.load(model_path, map_location="cpu")
    loaded.eval()
    return loaded


def _ensure_model() -> torch.nn.Module:
    global _model
    if _model is None:
        _model = _load_model()
    return _model


def _vectorize_features(features: dict[str, float]) -> torch.Tensor:
    missing = [name for name in FEATURE_NAMES if name not in features]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required features: {', '.join(missing)}")

    row = [float(features[name]) for name in FEATURE_NAMES]
    return torch.tensor([row], dtype=torch.float32)


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/invocations")
def invocations(payload: InvocationRequest) -> dict[str, float | int]:
    model = _ensure_model()
    input_tensor = _vectorize_features(payload.features)
    with torch.inference_mode():
        logits = model(input_tensor)
        probability = torch.sigmoid(logits).reshape(-1)[0].item()
    prediction = int(probability >= 0.5)
    return {"prediction": prediction, "probability": float(probability)}
