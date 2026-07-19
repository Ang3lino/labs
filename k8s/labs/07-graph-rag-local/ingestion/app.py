import json
import re
from pathlib import Path

from fastapi import FastAPI
from neo4j import GraphDatabase

app = FastAPI()
URI = "bolt://neo4j:7687"
AUTH = ("neo4j", "graphrag123")
DOCS = Path("sample-data/documents.json")
stats = {"docs": 0, "nodes": 0, "edges": 0}


def embed(text: str, size: int = 12) -> list[float]:
    # ponytail: swap for sentence-transformers in prod
    v = [0.0] * size
    for w in re.findall(r"[a-z0-9-]+", text.lower()):
        v[hash(w) % size] += 1.0
    s = sum(v) or 1.0
    return [round(x / s, 4) for x in v]


def upsert(tx, label: str, name: str, doc: dict):
    tx.run(
        f"MERGE (n:{label} {{name:$name}}) "
        "SET n.title=$title, n.content=$content, n.tags=$tags, n.embedding=$embedding",
        name=name,
        title=doc["title"],
        content=doc["content"],
        tags=doc["tags"],
        embedding=embed(doc["content"]),
    )


@app.post("/ingest")
def ingest():
    docs = json.loads(DOCS.read_text(encoding="utf-8"))
    with GraphDatabase.driver(URI, auth=AUTH) as drv, drv.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        for d in docs:
            label = {"incident": "Incident", "runbook": "Runbook"}.get(d["type"], "Service")
            name = re.search(r"([a-z]+-service|redis|postgres|session-service)", d["content"])
            s.execute_write(upsert, label, name.group(1) if name else d["id"], d)
            stats["nodes"] += 1
            if d["type"] == "incident":
                for svc in re.findall(r"[a-z]+-service", d["content"]):
                    s.run("MERGE (x:Service {name:$s}) MERGE (i:Incident {name:$i}) MERGE (x)-[:AFFECTED_BY]->(i)", s=svc, i=d["id"])
                    stats["edges"] += 1
            if d["type"] == "runbook" and "redis" in d["content"].lower():
                for svc in ["auth-service", "session-service"]:
                    s.run("MERGE (c:Component {name:'redis'}) MERGE (x:Service {name:$s}) MERGE (x)-[:USES]->(c)", s=svc)
                    stats["edges"] += 1
            for a, b in re.findall(r"([a-z]+-service).+?([a-z]+-service)", d["content"]):
                s.run("MERGE (a:Service {name:$a}) MERGE (b:Service {name:$b}) MERGE (a)-[:COMMUNICATES_WITH]->(b)", a=a, b=b)
                stats["edges"] += 1
        deps = [("api-gateway", "auth-service"), ("api-gateway", "payment-service"), ("payment-service", "user-service")]
        for src, dst in deps:
            s.run("MERGE (a:Service {name:$a}) MERGE (b:Service {name:$b}) MERGE (a)-[:DEPENDS_ON]->(b)", a=src, b=dst)
            stats["edges"] += 1
        stats["docs"] = len(docs)
    return {"status": "ingested", **stats}


@app.get("/status")
def status():
    return stats
