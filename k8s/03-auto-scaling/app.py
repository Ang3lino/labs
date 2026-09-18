import time

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
    # ponytail: artificial latency to make CPU work visible for HPA lab
    time.sleep(0.1)
    probs = model.predict_proba([payload.features])[0]
    idx = int(probs.argmax())
    return {"prediction": labels[idx], "confidence": round(float(probs[idx]), 2)}
