# MLOps & AI Infrastructure Labs

Hands-on labs covering the on-prem AI platform stack. Designed around the Pareto principle: learn the 20% that lets you understand 80% of production ML infrastructure.

## What You'll Build

By the end of these 6 labs, you'll have deployed an LLM on Kubernetes with GPU scheduling, served it via an OpenAI-compatible API, connected a RAG pipeline, and monitored everything with production-grade dashboards.

## Stack Covered

| Technology | Why It Matters | Lab |
|---|---|---|
| Docker | Everything runs in containers. Table stakes. | 01 |
| Kubernetes | The operating system of the cloud. Every MLOps JD lists it. | 02 |
| NVIDIA GPU Operator | GPU scheduling on K8s. Required for any ML workload. | 03 |
| vLLM + KServe | LLM inference serving. The hottest skill in ML infra (2025-2026). | 04 |
| RAG (Vector DB + Embeddings) | Every enterprise AI app needs retrieval-augmented generation. | 05 |
| Prometheus + Grafana | Production observability. SRE/platform roles require this. | 06 |
| Argo CD | GitOps CD for K8s. Declarative deployments, drift detection, fleet management. | 07 |
| KubeRay | Distributed Ray clusters on K8s. Multi-node LLM inference, autoscaling. | 08 |

## Learning Path (Incremental)

```
Lab 01         Lab 02          Lab 03          Lab 04          Lab 05       Lab 06         Lab 07       Lab 08
Docker    ───> Kubernetes ───> GPU on K8s ───> vLLM+KServe ───> RAG    ───> Monitoring ───> Argo CD ───> KubeRay
containers     pods/svc/       nvidia-gpu      model serving    vector DB   dashboards     GitOps CD    distributed
               deploy          operator        autoscaling      embeddings  alerts/SLOs    sync waves   inference
```

Each lab builds on the previous. Don't skip ahead.

## Prerequisites

- Docker Desktop or Podman
- kubectl + minikube (or kind)
- Python 3.11+ with uv
- ~16GB RAM (for local K8s + LLM serving)
- NVIDIA GPU recommended for labs 03-06 (CPU fallback provided)

## Lab Format

Each lab includes:
- **Summary** — what you'll build and why
- **Problem It Solves** — the real-world pain this addresses
- **How It Works Under the Hood** — internals, not just "kubectl apply"
- **Alternatives & When to Pick This** — decision framework
- **Industry Scenarios** — how companies actually use this
- **Interview Talking Points** — what to say when asked
- **Exercises** — hands-on, runnable locally
- **References** — where to go deeper

## Time Estimate

| Lab | Topic | Time |
|---|---|---|
| 01 | Containers | 3-4 hours |
| 02 | Kubernetes Core | 6-8 hours |
| 03 | GPU on K8s | 3-4 hours |
| 04 | vLLM + KServe | 4-6 hours |
| 05 | RAG Pipeline | 4-6 hours |
| 06 | Observability | 3-4 hours |
| 07 | Argo CD GitOps | 4-6 hours |
| 08 | KubeRay Distributed Inference | 4-6 hours |
| **Total** | | **~33-42 hours** |

## Industry Context

This stack maps directly to real ML platform roles:

| Role | Uses Labs |
|---|---|
| MLOps Engineer | All 8 |
| ML Platform Engineer | 02, 03, 04, 06, 07, 08 |
| AI Engineer | 04, 05, 08 |
| SRE / Platform | 02, 03, 06, 07 |

## Quick Start

```bash
cd 01-containers && cat README.md
```
