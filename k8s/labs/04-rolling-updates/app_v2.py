from fastapi import FastAPI

app = FastAPI(title="sentiment-model-v2")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_version": "v2"}


@app.post("/predict")
def predict(payload: dict) -> dict:
    # ponytail: constant response keeps focus on deployment strategy learning
    _ = payload
    return {
        "model_version": "v2",
        "prediction": "positive",
        "confidence": 0.91,
    }
