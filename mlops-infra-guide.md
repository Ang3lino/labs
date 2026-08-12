# ML/AI Infrastructure — Decision Guide

Personal reference for choosing the right tool per use case. Based on hands-on experience with `translator`, `media-swap-face`, `file-analyzer`, and the HPE AI Platform project.

## The Mental Model

```
┌─────────────────────────────────────────────────────────────────┐
│                    What problem are you solving?                  │
│                                                                  │
│  "What happened?"           → MLflow (experiment tracking)       │
│  "Run this function on N GPUs" → Ray (distributed compute)      │
│  "Run these containers 24/7"   → K8s (infrastructure platform)  │
│  "Run steps in order, retry"   → Airflow/Prefect (orchestration)│
│  "Show me live metrics"        → Grafana / W&B (monitoring)     │
│  "Version my data"             → DVC (data versioning)          │
└─────────────────────────────────────────────────────────────────┘
```

## Tool Comparison Matrix

### Experiment Tracking — "Which params gave best results?"

| Tool | Best for | Market demand | On-prem? |
|---|---|---|---|
| **MLflow** | Universal tracker, model registry | Very high (Databricks ecosystem) | Yes |
| **W&B** | Real-time training curves, team collaboration | High (research/startups) | SaaS only |
| **Aim** | Lightest self-hosted alternative | Low-medium | Yes |

### Pipeline Orchestration — "Run steps in order, handle failures"

| Tool | Best for | Market demand | On-prem? |
|---|---|---|---|
| **Airflow** | Data engineering, broad adoption | Very high (inherited by ML teams) | Yes |
| **Prefect** | Best Python DX, least boilerplate | Medium (growing) | Yes |
| **Kubeflow Pipelines** | ML-native orchestration on K8s | High (ML platform roles) | Yes (needs K8s) |
| **SageMaker Pipelines** | AWS ML lifecycle | Very high (AWS roles) | No (AWS only) |
| **Dagster** | Asset-oriented, great UI | Low-medium | Yes |

### Distributed Compute — "Use more GPUs / machines"

| Tool | Best for | Market demand | On-prem? |
|---|---|---|---|
| **Ray** | Python-native distributed compute, burst GPU | High (growing fast) | Yes |
| **K8s** | Container orchestration, multi-tenant platform | Very high (universal) | Yes |

### Model Serving — "Expose model as API, auto-scale"

| Tool | Best for | Market demand | On-prem? |
|---|---|---|---|
| **KServe (K8s)** | Production model serving on K8s | High | Yes |
| **Ray Serve** | Simpler serving, Python-native | Medium | Yes |
| **vLLM / TGI** | LLM inference specifically | High (growing) | Yes |
| **SageMaker Endpoints** | AWS-managed serving | Very high | No |

### Real-Time Monitoring — "Live dashboards while pipeline runs"

| Tool | Best for | Market demand | On-prem? |
|---|---|---|---|
| **Grafana + Prometheus** | Custom infra dashboards, sub-second | Very high | Yes |
| **W&B** | Training curves, system metrics | High | SaaS |
| **Ray Dashboard** | Ray task/actor monitoring | Included with Ray | Yes |
| **MLflow** (`log_system_metrics=True`) | Basic CPU/RAM per run | Included with MLflow | Yes |

## When to Use What — Decision Tree

```
Q: Are you ONE person running ONE job on ONE machine?
   YES → just run it. multiprocessing for CPU parallelism. No orchestrator needed.
   NO ↓

Q: Do you need MORE GPUs than one machine has?
   YES → Ray (simplest) or K8s (most universal)
   NO ↓

Q: Do you need the pipeline to survive failures / SSH drops?
   YES → Prefect (lightest) or Airflow (most demanded)
   NO ↓

Q: Do you need to compare experiment params vs metrics?
   YES → MLflow
   NO → just run the script.
```

## Ray vs K8s — When Each Wins

```
Ray:  "Run this Python function on N GPUs"
K8s:  "Run these containers as reliable services"
Both: Can provision machines, auto-scale, schedule GPU work
```

| Scenario | Winner | Why |
|---|---|---|
| Fan-out GPU compute (batch) | **Ray** | Python decorators, automatic data passing, less code |
| Serving models as APIs 24/7 | **K8s** | Health checks, rolling deploys, multi-tenant, ingress |
| Multi-team platform | **K8s** | RBAC, namespaces, resource quotas |
| One person, burst compute | **Ray** | `pip install ray` vs "set up K8s cluster" |
| Mixed language services | **K8s** | Any container, not just Python |
| Quick experiments with scaling | **Ray** | Same code local ↔ cluster |
| Production enterprise infra | **K8s** | Industry standard, every cloud supports it |

### Can they work together?

Yes — **KubeRay**: Ray runs as pods inside K8s. K8s handles infra (nodes, networking, storage), Ray handles Python compute distribution. This is what large companies do.

## Cloud-Agnostic vs Cloud-Native

| Cloud-agnostic (portable skills) | Cloud-native (vendor locked) |
|---|---|
| MLflow, Ray, K8s, Airflow, Prefect | SageMaker, Vertex AI, Azure ML |
| Run anywhere: laptop, VM, any cloud | Run only on that vendor |
| Skills transfer across JDs | Skills locked to one ecosystem |

**Interview defense**: "I use MLflow + Ray + K8s — they deploy identically on EKS, AKS, GKE, or bare metal. The pipeline code doesn't change, only the infra provisioning."

## Market Demand (ML/AI roles, 2026)

```
SageMaker         ████████████████████████████████  #1 on AWS ML JDs
MLflow            ██████████████████████████████    universal tracker
K8s               ██████████████████████████████    universal infra (platform roles)
Kubeflow          ████████████████████              ML platform roles
Ray               ████████████████████              fastest growing in ML
W&B               ██████████████                    research/startup teams
Airflow           ██████████████████████████        data eng (inherited by ML)
Prefect           ████████                          growing, not yet on most JDs
Dagster           ██████                            niche
Metaflow          ████                              rare
```

## My Stack — What I Use Where

| Project | Tools | Why |
|---|---|---|
| **file-analyzer** | MLflow | Simple batch tracking, 4 files |
| **translator** | Ray + MLflow | Burst GPU compute + quality tracking |
| **media-swap-face** | K8s + Ray | Serve as API (K8s) + batch processing (Ray) |
| **HPE AI Platform** | K8s + KServe + MLflow + Kubeflow | Multi-team LLM serving platform |

## Key Insights

1. **K8s is for multi-tenant services, not batch scripts.** If you're 1 person running 1 job, K8s is ceremony for nothing.

2. **Ray is the "K8s for Python compute."** Same scaling, 5x less code, but only for Python workloads.

3. **MLflow is the universal ledger.** Every other tool complements it, none replaces it.

4. **Airflow dominates by inertia, not quality.** Learn it for interviews, use Prefect for yourself.

5. **Cloud-native tools (SageMaker) lock you in.** Cloud-agnostic tools (MLflow, Ray, K8s) are portable across JDs.

6. **"Better on paper" ≠ "better for career."** Dagster > Airflow technically, but Airflow has 20x the job listings.

7. **The winning combo**: Ray (compute) + K8s (serving) + MLflow (tracking). Covers every ML/AI JD requirement.

## Quick Reference — Code Snippets

### MLflow — Track an experiment
```python
import mlflow
mlflow.set_experiment("my-experiment")
with mlflow.start_run(run_name="run-1", log_system_metrics=True):
    mlflow.log_params({"model": "gemma3:27b", "batch_size": 40})
    mlflow.log_metrics({"bleu": 0.72, "latency_s": 1.2})
    mlflow.log_artifact("output.srt")
```

### Ray — Fan out GPU work
```python
import ray
ray.init()

@ray.remote(num_gpus=1, max_retries=3)
def process(chunk):
    return heavy_gpu_work(chunk)

futures = [process.remote(c) for c in chunks]  # N GPUs in parallel
results = ray.get(futures)                      # collect all
```

### K8s — GPU Job
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: inference-job
spec:
  template:
    spec:
      containers:
      - name: worker
        image: my-model:latest
        resources:
          limits:
            nvidia.com/gpu: 1
      restartPolicy: Never
```

### K8s — Model serving (KServe)
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: llm-service
spec:
  predictor:
    model:
      modelFormat: vllm
      resources:
        limits:
          nvidia.com/gpu: 4
    minReplicas: 1
    maxReplicas: 10
```

### Prefect — Orchestrated pipeline (if needed)
```python
from prefect import flow, task

@task(retries=3, cache_key_fn=task_input_hash)
def translate(segments):
    return run_translation(segments)

@flow(log_prints=True)
def pipeline(video):
    audio = extract(video)
    segments = transcribe(audio)
    translated = translate(segments)
    return translated
```
