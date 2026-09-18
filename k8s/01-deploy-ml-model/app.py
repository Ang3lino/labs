from joblib import load
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()
model = load("model.pkl")
labels = ["setosa", "versicolor", "virginica"]


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/predict")
def predict(payload: PredictRequest) -> dict[str, float | str]:
    probs = model.predict_proba([payload.features])[0]
    idx = int(probs.argmax())
    confidence = round(float(probs[idx]), 2)
    # ponytail: no feature validation pipeline to keep first lab focused on K8s basics
    return {"prediction": labels[idx], "confidence": confidence}
