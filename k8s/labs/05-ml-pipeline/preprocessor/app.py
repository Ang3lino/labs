from fastapi import FastAPI

app = FastAPI(title="preprocessor")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "preprocessor"}


@app.post("/preprocess")
def preprocess(payload: dict) -> dict:
    text = str(payload.get("text", ""))
    # ponytail: minimal preprocessing to isolate service-boundary learning
    cleaned = text.strip().lower()
    return {"cleaned": cleaned}
