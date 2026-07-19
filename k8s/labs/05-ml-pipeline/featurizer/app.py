from fastapi import FastAPI

app = FastAPI(title="featurizer")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "featurizer"}


@app.post("/featurize")
def featurize(payload: dict) -> dict:
    cleaned = str(payload.get("cleaned", ""))
    seed = sum(ord(char) for char in cleaned)
    # ponytail: fake TF-IDF-like vector from deterministic hash math
    raw = [((seed + i * 17) % 100) / 100 for i in range(6)]
    total = sum(raw) or 1.0
    features = [round(value / total, 4) for value in raw]
    return {"features": features}
