from fastapi import FastAPI
import httpx

PREPROCESSOR_URL = "http://preprocessor:8080/preprocess"
FEATURIZER_URL = "http://featurizer:8080/featurize"

app = FastAPI(title="inference")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "inference"}


@app.post("/predict")
async def predict(payload: dict) -> dict:
    text = str(payload.get("text", ""))

    async with httpx.AsyncClient(timeout=5.0) as client:
        preprocess = await client.post(PREPROCESSOR_URL, json={"text": text})
        preprocess.raise_for_status()
        cleaned = preprocess.json()["cleaned"]

        featurize = await client.post(FEATURIZER_URL, json={"cleaned": cleaned})
        featurize.raise_for_status()
        features = featurize.json()["features"]

    score = sum(features)
    # ponytail: deterministic threshold keeps focus on service-to-service flow
    prediction = "positive" if score >= 0.5 else "negative"
    return {
        "prediction": prediction,
        "pipeline": {"cleaned": cleaned, "features": features},
    }
