import json
from pathlib import Path

from fastapi import FastAPI
from neo4j import GraphDatabase

app = FastAPI()
URI = "bolt://neo4j:7687"
AUTH = ("neo4j", "graphrag123")
BASE = Path("/data")


@app.post("/build-graph")
def build_graph():
    events = json.loads((BASE / "ecs-task-events.json").read_text(encoding="utf-8"))
    errs = json.loads((BASE / "cloudwatch-errors.json").read_text(encoding="utf-8"))
    deps = json.loads((BASE / "service-dependencies.json").read_text(encoding="utf-8"))
    with GraphDatabase.driver(URI, auth=AUTH) as d, d.session() as s:
        s.run("MATCH (n) DETACH DELETE n")
        for e in events:
            s.run("MERGE (c:Cluster {name:$c})", c=e.get("cluster", "prod-cluster"))
            s.run("MERGE (sv:Service {name:$s})", s=e["service"])
            s.run(
                "MERGE (t:Task {id:$id}) SET t.event=$ev, t.ts=$ts, t.reason=$r, t.exit_code=$x "
                "MERGE (sv:Service {name:$s})-[:RUNS_ON]->(c:Cluster {name:$c}) MERGE (sv)-[:HAS_TASK]->(t)",
                id=e["task_id"],
                ev=e["event"],
                ts=e["timestamp"],
                r=e.get("reason", ""),
                x=e.get("exit_code", 0),
                s=e["service"],
                c=e.get("cluster", "prod-cluster"),
            )
            for dep in e.get("dependencies", []):
                s.run("MERGE (a:Service {name:$a}) MERGE (b:Service {name:$b}) MERGE (a)-[:COMMUNICATES_WITH]->(b)", a=e["service"], b=dep)
        for dmap in deps:
            for dep in dmap["depends_on"]:
                s.run("MERGE (a:Service {name:$a}) MERGE (b:Service {name:$b}) MERGE (a)-[:DEPENDS_ON]->(b)", a=dmap["service"], b=dep)
        prev = {}
        for er in errs:
            s.run("CREATE (e:Error {id:randomUUID(), trace_id:$t, service:$s, msg:$m, ts:$ts})", t=er["trace_id"], s=er["service"], m=er["message"], ts=er["timestamp"])
            s.run("MATCH (sv:Service {name:$s}), (e:Error {trace_id:$t, service:$s}) MERGE (sv)-[:PRODUCED_ERROR]->(e)", s=er["service"], t=er["trace_id"])
            if er["trace_id"] in prev:
                s.run(
                    "MATCH (a:Error {trace_id:$t, service:$from}), (b:Error {trace_id:$t, service:$to}) MERGE (a)-[:CAUSED]->(b)",
                    t=er["trace_id"],
                    from=prev[er["trace_id"]],
                    to=er["service"],
                )
            prev[er["trace_id"]] = er["service"]
        s.run(
            "MATCH (s:Service) OPTIONAL MATCH (s)-[:PRODUCED_ERROR]->(e:Error) OPTIONAL MATCH (s)-[:HAS_TASK]->(t:Task) "
            "WITH s, count(DISTINCT e) AS err, sum(CASE WHEN t.event='STOPPED' THEN 1 ELSE 0 END) AS rst, "
            "sum(CASE WHEN t.event='RUNNING' THEN 1 ELSE 0 END) AS run, count(DISTINCT t) AS total "
            "SET s.error_count=err, s.restart_count=rst, s.avg_uptime=CASE WHEN total=0 THEN 0 ELSE toFloat(run)/toFloat(total) END"
        )
    return {"status": "built", "events": len(events), "errors": len(errs), "services": len(deps)}


@app.get("/health")
def health():
    return {"status": "ok"}
