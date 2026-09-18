from fastapi import FastAPI

app = FastAPI(title="sentiment-model-v1")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_version": "v1"}


@app.post("/predict")
def predict(payload: dict) -> dict:
    # ponytail: constant response keeps focus on rollout behavior, not model logic
    _ = payload
    return {
        "model_version": "v1",
        "prediction": "positive",
        "confidence": 0.78,
    }
