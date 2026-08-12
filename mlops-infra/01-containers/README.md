# Lab 01 — Containers (Docker)

## Summary

Package an ML inference script into a Docker container that runs identically on your laptop, a server, or Kubernetes. By the end you'll have a GPU-ready multi-stage image under 1GB.

## Problem It Solves

"Works on my machine" kills ML teams. Your model needs CUDA 12.4, PyTorch 2.7, a specific tokenizer version, and ffmpeg. Without containers:
- New team member spends 2 days setting up the environment
- Production server has different library versions → model outputs differ
- "Which Python was this trained with?" → nobody knows

Containers freeze the entire runtime into a reproducible, shippable artifact.

## How It Works Under the Hood

```
┌─────────────────────────────────────────────────────────┐
│ Host Machine (Linux kernel)                              │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Container A  │  │ Container B  │  │ Container C  │  │
│  │ Python 3.12  │  │ Python 3.10  │  │ Node 20      │  │
│  │ PyTorch 2.7  │  │ TensorFlow   │  │ Express      │  │
│  │ CUDA 12.4    │  │ CUDA 11.8    │  │ No GPU       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                          │
│  Shared kernel, isolated filesystem + network + PIDs     │
└─────────────────────────────────────────────────────────┘
```

**Key internals:**
- **Namespaces** — each container gets isolated PID, network, mount, user namespaces
- **cgroups** — limit CPU, memory, GPU access per container
- **Union filesystem (OverlayFS)** — layers stack; shared base layers aren't duplicated
- **Image = layers** — each Dockerfile instruction creates a layer; layers cache independently
- **NVIDIA Container Toolkit** — exposes GPU devices (`/dev/nvidia0`) into container via `--gpus all`

**Image build process:**
```
Dockerfile → docker build → layer cache check → execute instructions → tag image
                                    ↓
                          If layer unchanged → skip (cached)
                          If changed → rebuild this + all subsequent layers
```

**Why layer order matters for ML:**
```dockerfile
# GOOD: deps change rarely, code changes often
COPY requirements.txt .        # layer 1: cached unless deps change
RUN pip install -r requirements.txt  # layer 2: cached
COPY src/ ./src/               # layer 3: rebuilt on code change (cheap)

# BAD: code change invalidates expensive pip install
COPY . .                       # layer 1: always changes
RUN pip install -r requirements.txt  # layer 2: always rebuilt (slow)
```

## Alternatives & When to Pick

| Tool | When to pick | When NOT |
|---|---|---|
| **Docker** | Standard. Works everywhere. Default choice. | Windows-native apps, security-hardened environments banning Docker daemon |
| **Podman** | Daemonless, rootless. Required in some enterprise (Red Hat/OpenShift). | When your CI/tooling assumes Docker socket |
| **Apptainer (Singularity)** | HPC clusters where root access is forbidden | General web/ML serving |
| **Conda** | Environment isolation only (no runtime packaging) | Production deployment (not a container) |
| **uv/venv** | Lightweight Python isolation | When you need OS-level deps (CUDA, ffmpeg) |

**Decision rule**: If it runs on K8s or needs to be shipped → Docker. If it's just local Python isolation → uv/venv.

## Industry Scenarios

| Company Pattern | How Containers Are Used |
|---|---|
| **HPE AI Platform** (your project) | Every model runtime (vLLM, Triton) runs in GPU containers on K8s |
| **Netflix** | All ML training + inference runs in Docker on Titus (their container platform) |
| **Uber** | Michelangelo platform packages every model as a Docker image with pinned deps |
| **Any startup** | Docker → ECR/GCR → K8s/ECS. Standard deployment path. |
| **ML competition** | Kaggle/DrivenData require Docker submission for reproducibility |

## Key Terms

- `Dockerfile` — build recipe
- `Image` — immutable artifact (layers)
- `Container` — running instance of an image
- `Registry` (Docker Hub, ECR, GCR) — image storage
- `Multi-stage build` — separate build env from runtime (smaller images)
- `NVIDIA Container Toolkit` — GPU passthrough to containers
- `ENTRYPOINT` vs `CMD` — fixed command vs overridable defaults
- `Volume mount (-v)` — share host files with container
- `--gpus all` — expose all GPUs to container

## Interview Talking Points

"I containerize all ML workloads with multi-stage Docker builds. Base image is NVIDIA CUDA runtime, I copy only the inference code and model weights into the final stage — keeps images under 2GB. I use layer ordering to cache pip installs separately from code changes, cutting CI build times from 15 min to 2 min. Images are pushed to ECR and deployed via K8s Deployments with GPU resource requests."

## Exercises

### Exercise 1: Containerize an inference script

Create a `Dockerfile` that packages a simple model inference script:

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY inference.py .
ENTRYPOINT ["python", "inference.py"]
```

```python
# inference.py
import sys
from transformers import pipeline

classifier = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
text = sys.argv[1] if len(sys.argv) > 1 else "This lab is fantastic"
print(classifier(text))
```

```bash
docker build -t ml-inference .
docker run --rm ml-inference "Kubernetes is powerful"
```

### Exercise 2: Multi-stage GPU build

```dockerfile
# Stage 1: install deps (large, cached)
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04 AS builder
RUN apt-get update && apt-get install -y python3 python3-pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: runtime (only what's needed)
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04
RUN apt-get update && apt-get install -y python3 && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/lib/python3.*/dist-packages /usr/local/lib/python3.*/dist-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY src/ /app/src/
WORKDIR /app
ENTRYPOINT ["python3", "-m", "src.serve"]
```

```bash
docker build -t ml-gpu .
docker run --rm --gpus all ml-gpu
```

### Exercise 3: Layer caching experiment

1. Build the image from Exercise 1
2. Change `inference.py` (add a print statement)
3. Rebuild — observe which layers are cached vs rebuilt
4. Now change `requirements.txt` — observe everything after it rebuilds

### Exercise 4: Inspect image internals

```bash
docker history ml-inference          # see layers + sizes
docker inspect ml-inference          # see config, env vars, entrypoint
docker run --rm -it ml-inference sh  # shell into container, explore filesystem
```

### Exercise 5: Push to registry

```bash
# Tag for Docker Hub (or use local registry for air-gapped)
docker tag ml-inference youruser/ml-inference:v1
docker push youruser/ml-inference:v1

# Or run a local registry
docker run -d -p 5000:5000 registry:2
docker tag ml-inference localhost:5000/ml-inference:v1
docker push localhost:5000/ml-inference:v1
```

## References

- [Docker official docs — Best practices](https://docs.docker.com/build/building/best-practices/)
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
- [Multi-stage builds](https://docs.docker.com/build/building/multi-stage/)
- *Designing Machine Learning Systems* Ch.7 (Model Deployment)
