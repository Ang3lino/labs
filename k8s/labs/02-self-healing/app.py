from joblib import load
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI()
model = load("model.pkl")
labels = ["setosa", "versicolor", "virginica"]
predict_count = 0


class PredictRequest(BaseModel):
    features: list[float]


@app.get("/health")
def health() -> dict[str, str]:
    if predict_count > 50:
        raise HTTPException(status_code=500, detail="degraded")
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    if model is None:
        raise HTTPException(status_code=500, detail="model_not_loaded")
    return {"status": "ready"}


@app.post("/predict")
def predict(payload: PredictRequest) -> dict[str, float | str | int]:
    global predict_count
    predict_count += 1
    probs = model.predict_proba([payload.features])[0]
    idx = int(probs.argmax())
    confidence = round(float(probs[idx]), 2)
    # ponytail: counter-based failure simulates memory-leak degradation pattern
    return {
        "prediction": labels[idx],
        "confidence": confidence,
        "request_count": predict_count,
    }
