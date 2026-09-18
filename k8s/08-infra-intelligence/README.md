# Lab 08: Infra Intelligence — ECS Log Analysis with Graph RAG

This capstone extends Lab 07 into a cloud-ops use case: build an AI-facing infrastructure intelligence layer from ECS task events and CloudWatch-style errors.

## Scenario

Your company runs a digital twin system on AWS ECS. You have months of CloudWatch logs, ECS task events, and service dependency metadata. Build a Graph RAG system that answers:

- Which services are most critical?
- What fails if `mqtt-broker` goes down?
- What error cascade happened during an OOM?
- Which services generate the most errors?

Lab 08 reuses Neo4j/K8s patterns from Lab 07, but is deployable independently.

## What You'll Learn

- Converting infra telemetry into graph entities and edges
- Running graph build as a Kubernetes Job data pipeline
- Using ConfigMaps for static lab datasets
- Querying service criticality, cascades, and health summaries from Neo4j

## What This Proves to Recruiters

- "I build AI systems that provide operational intelligence on cloud infrastructure."
- You can turn raw infra events into graph-native reasoning artifacts
- You can deploy and operate batch + online API components on Kubernetes

## Architecture Diagram (ASCII)

```text
  ECS Task Events + CloudWatch Errors + Dependency Map
                     |  (ConfigMap mounted JSON)
                     v
           +----------------------------+
           | graph-builder Job (:8080) |
           | - build graph + metrics    |
           +-------------+--------------+
                         |
                         | bolt://neo4j:7687
                         v
           +----------------------------+
           | Neo4j StatefulSet          |
           | persistent graph storage   |
           +-------------+--------------+
                         ^
                         |
           +-------------+--------------+
User ----> | query-api Deployment       |
Query      | natural-language patterns  |
           +----------------------------+
```

## Prerequisites

- Complete Lab 07 (recommended) or equivalent Neo4j-on-K8s basics
- Docker Desktop with Kubernetes enabled
- `kubectl` and Docker installed

## Step-by-Step Instructions

1) Build images:

```bash
docker build -t ml-lab-08-graph-builder:latest -f graph-builder/Dockerfile .
docker build -t ml-lab-08-query-api:latest -f query-api/Dockerfile .
```

2) Deploy stack:

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/neo4j-secret.yaml
kubectl apply -f k8s/configmap-data.yaml
kubectl apply -f k8s/neo4j.yaml
kubectl apply -f k8s/graph-builder-job.yaml
kubectl apply -f k8s/query-api.yaml
```

3) Watch status:

```bash
kubectl -n infra-intelligence get pods -w
```

4) Port-forward query API:

```bash
kubectl -n infra-intelligence port-forward svc/query-api 8080:8080
```

## Verification Steps

```bash
kubectl -n infra-intelligence get all
kubectl -n infra-intelligence logs job/infra-graph-builder
curl http://localhost:8080/health
```

Expected:
- Neo4j ready
- graph-builder Job completed
- query-api healthy

## Sample Queries to Try

```bash
# Which service is most critical (most things depend on it)?
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "most critical service"}'

# What breaks if mqtt-broker goes down?
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "what fails if mqtt-broker goes down"}'

# Show the error cascade from the digital-twin-sync OOM
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "error cascade for digital-twin-sync"}'

# Which services have the most errors?
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "services with most errors"}'

# Overall health summary
curl -X POST http://localhost:8080/query -H "Content-Type: application/json" -d '{"question": "health summary"}'
```

## Cleanup

```bash
kubectl delete -f k8s/query-api.yaml
kubectl delete -f k8s/graph-builder-job.yaml
kubectl delete -f k8s/neo4j.yaml
kubectl delete -f k8s/configmap-data.yaml
kubectl delete -f k8s/neo4j-secret.yaml
kubectl delete -f k8s/namespace.yaml
```

## Interview Talking Points

- "I built an infrastructure intelligence system that ingests ECS task events and CloudWatch-style errors into a Neo4j knowledge graph."
- "I enabled natural-language-ish graph queries for criticality, failure cascades, and service health trends."
- "I deployed it on Kubernetes with persistent graph storage, batch graph build jobs, and horizontally scalable query APIs."

## ConfigMap vs Baked Data Tradeoff

This lab uses a ConfigMap so you can edit data without rebuilding the image. For real production volumes, ingest from object storage or stream processors instead.
