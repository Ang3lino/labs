import re

from fastapi import FastAPI
from neo4j import GraphDatabase
from pydantic import BaseModel

app = FastAPI()
URI = "bolt://neo4j:7687"
AUTH = ("neo4j", "graphrag123")


class QueryBody(BaseModel):
    question: str


@app.post("/query")
def query(body: QueryBody):
    q = body.question.lower()
    with GraphDatabase.driver(URI, auth=AUTH) as d, d.session() as s:
        if "most critical" in q:
            row = s.run(
                "MATCH (a:Service)<-[:DEPENDS_ON]-(b:Service) RETURN a.name AS service, count(b) AS dependents ORDER BY dependents DESC LIMIT 1"
            ).single()
            return {"summary": f"Most critical service is {row['service']} with {row['dependents']} dependents.", "graph": dict(row)}
        if "what fails if" in q:
            m = re.search(r"what fails if\s+([a-z-]+)", q)
            name = m.group(1) if m else "mqtt-broker"
            rows = s.run("MATCH (a:Service)-[:DEPENDS_ON*1..3]->(b:Service {name:$n}) RETURN DISTINCT a.name AS s", n=name).data()
            affected = [r["s"] for r in rows]
            return {"summary": f"If {name} goes down, likely impacted: {', '.join(affected) or 'none'}.", "graph": {"root": name, "affected": affected}}
        if "error cascade" in q:
            trace = "TR-001" if "tr-" not in q else re.search(r"tr-\d+", q).group(0).upper()
            rows = s.run("MATCH (a:Error {trace_id:$t})-[:CAUSED]->(b:Error {trace_id:$t}) RETURN a.service AS from, b.service AS to", t=trace).data()
            return {"summary": f"Cascade edges for {trace}: {len(rows)}", "graph": rows}
        if "most errors" in q:
            rows = s.run("MATCH (s:Service) RETURN s.name AS service, coalesce(s.error_count,0) AS errors ORDER BY errors DESC LIMIT 5").data()
            return {"summary": "Top services by error count.", "graph": rows}
        if "health summary" in q:
            row = s.run(
                "MATCH (s:Service) RETURN count(s) AS services, sum(coalesce(s.error_count,0)) AS total_errors, "
                "sum(coalesce(s.restart_count,0)) AS total_restarts, avg(coalesce(s.avg_uptime,0.0)) AS avg_uptime"
            ).single()
            return {"summary": "Overall infrastructure health snapshot.", "graph": dict(row)}
    return {"summary": "Pattern not supported. Try: most critical service, what fails if X goes down, error cascade, most errors, health summary.", "graph": {}}


@app.get("/health")
def health():
    return {"status": "ok"}
