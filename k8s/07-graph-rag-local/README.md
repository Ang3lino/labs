# Lab 07: Graph RAG on K8s (Local)

This is a **portfolio capstone** lab: you deploy a graph-powered retrieval system on Kubernetes and answer infra questions from relationship-aware data, not keyword search alone.

## Scenario

Your team has internal documentation scattered across wikis, runbooks, and incident reports. You need a Graph RAG system that understands relationships between services/components and can answer questions like:

- What depends on `auth-service`?
- What's the blast radius if Redis goes down?
- Which service has the most dependencies?
- What incidents affected `payment-service`?

## What You'll Learn

- Why Neo4j runs better as a **StatefulSet** than a plain Deployment
- How to run one-time graph loading with a **Kubernetes Job**
- How to gate startup with an **initContainer** waiting on Neo4j
- How to use **Secrets** for Neo4j auth and **Namespaces** for isolation
- How to serve a Graph RAG API (template-based response) on port 8080

## What This Proves to Recruiters

- You can design and deploy a multi-service AI system on Kubernetes
- You understand graph-based retrieval for operational reasoning
- You can handle persistence (PVC), service discovery, and secret management
- You can build production-shaped systems from notebook-era skills

## Architecture Diagram (ASCII)

```text
                         +-----------------------------+
User Query  -----------> | rag-api (FastAPI, :8080)   |
                         | - parse intent/entities     |
                         | - query Neo4j subgraph      |
                         +--------------+--------------+
                                        |
                                        | bolt://neo4j:7687
                                        v
                         +-----------------------------+
                         | Neo4j (StatefulSet)         |
                         | :7474 HTTP / :7687 Bolt     |
                         +--------------+--------------+
                                        ^
                                        |
                         +--------------+--------------+
                         | ingestion Job (FastAPI app) |
                         | POST /ingest once            |
                         | loads docs + relationships   |
                         +-----------------------------+
```

## Prerequisites

- Docker Desktop + Kubernetes enabled
- `kubectl` installed
- Docker images built locally

```bash
kubectl version --client
docker version
```

## Step-by-Step Instructions

1) Build images from this lab root:

```bash
docker build -t ml-lab-07-ingestion:latest -f ingestion/Dockerfile .
docker build -t ml-lab-07-rag-api:latest -f rag-api/Dockerfile .
```

2) Apply manifests:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/neo4j-secret.yaml
kubectl apply -f k8s/neo4j.yaml
kubectl apply -f k8s/ingestion.yaml
kubectl apply -f k8s/rag-api.yaml
```

3) Watch rollout:

```bash
kubectl -n graph-rag get pods -w
```

4) If ingestion Job completed and you need to rerun:

```bash
kubectl -n graph-rag delete job graph-rag-ingestion
kubectl -n graph-rag apply -f k8s/ingestion.yaml
```

5) Port-forward the RAG API service:

```bash
kubectl -n graph-rag port-forward svc/rag-api 8080:8080
```

## Verification Steps

```bash
kubectl -n graph-rag get all
kubectl -n graph-rag logs job/graph-rag-ingestion
curl http://localhost:8080/health
```

Expected:
- Neo4j pod is Running and Ready
- ingestion Job is Completed
- `GET /health` returns `{ "status": "ok" }`

## Sample Queries to Try

```bash
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "What depends on auth-service?"}'
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "What is the blast radius if Redis goes down?"}'
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "Which service has the most dependencies?"}'
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "Show me recent incidents for payment-service"}'
```

## Cleanup

```bash
kubectl delete -f k8s/rag-api.yaml
kubectl delete -f k8s/ingestion.yaml
kubectl delete -f k8s/neo4j.yaml
kubectl delete -f k8s/neo4j-secret.yaml
kubectl delete -f k8s/namespace.yaml
```

## Interview Talking Points

- "I built and deployed a Graph RAG system on Kubernetes using Neo4j as a knowledge graph."
- "I used StatefulSet + PVC for graph persistence, a Job for ingestion, and a Deployment for query serving."
- "I implemented relationship-aware retrieval to answer blast-radius and dependency questions from infra documents."
- "I managed service discovery and secrets cleanly across a namespaced multi-service architecture."
