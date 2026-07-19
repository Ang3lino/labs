import re

from fastapi import FastAPI
from neo4j import GraphDatabase
from pydantic import BaseModel

app = FastAPI()
URI = "bolt://neo4j:7687"
AUTH = ("neo4j", "graphrag123")
SERVICES = [
    "auth-service",
    "user-service",
    "payment-service",
    "notification-service",
    "api-gateway",
    "session-service",
]


class QueryBody(BaseModel):
    question: str


def find_service(text: str) -> str | None:
    t = text.lower()
    return next((s for s in SERVICES if s in t), None)


@app.post("/query")
def query(body: QueryBody):
    q = body.question.lower()
    svc = find_service(q)
    with GraphDatabase.driver(URI, auth=AUTH) as drv, drv.session() as s:
        if "blast radius" in q or "redis" in q:
            rows = s.run("MATCH (c:Component {name:'redis'})<-[:USES]-(x:Service) RETURN x.name AS n").data()
            names = [r["n"] for r in rows]
            return {
                "answer": f"If Redis fails, likely impacted services are: {', '.join(names) or 'none found'}.",
                "sources": ["runbook redis outage", "component redis cache"],
                "graph_context": {"component": "redis", "affected": names},
            }
        if "most dependencies" in q:
            top = s.run(
                "MATCH (a:Service)-[:DEPENDS_ON]->(b:Service) RETURN a.name AS n, count(b) AS c ORDER BY c DESC LIMIT 1"
            ).single()
            return {"answer": f"{top['n']} has the most declared dependencies ({top['c']}).", "sources": ["dependency map"], "graph_context": dict(top)}
        if "incident" in q and svc:
            rows = s.run("MATCH (s:Service {name:$n})-[:AFFECTED_BY]->(i:Incident) RETURN i.name AS i", n=svc).data()
            incidents = [r["i"] for r in rows]
            return {"answer": f"Recent incidents for {svc}: {', '.join(incidents) or 'none'}.", "sources": incidents, "graph_context": {"service": svc, "incidents": incidents}}
        if svc:
            rows = s.run("MATCH (a:Service)-[:DEPENDS_ON]->(b:Service {name:$n}) RETURN a.name AS n", n=svc).data()
            deps = [r["n"] for r in rows]
            return {"answer": f"Services depending on {svc}: {', '.join(deps) or 'none found'}.", "sources": deps, "graph_context": {"service": svc, "dependents": deps}}
        keys = re.findall(r"[a-z]+-[a-z]+", q)
        return {"answer": "I could not map that question to a known graph pattern yet.", "sources": keys, "graph_context": {"question": body.question}}


@app.get("/health")
def health():
    return {"status": "ok"}
